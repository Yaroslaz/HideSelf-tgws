import copy
import os
import ssl
import sys
import unittest
from unittest import mock

import httpx

from proxy import bridge, raw_websocket, tg_ws_proxy
from proxy.cf_h2 import _HttpLane
from proxy.config import proxy_config
from proxy.pool import _CfWorkerPool


class RuntimeUpgradeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        previous = copy.deepcopy(vars(proxy_config))
        self.addCleanup(lambda: vars(proxy_config).update(previous))

    async def test_h2_dials_origin_directly_with_proxy_environment(self):
        proxies = {name: 'http://vpn-proxy.invalid:3128'
                   for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
                                'http_proxy', 'https_proxy', 'all_proxy')}
        proxies.update({'NO_PROXY': '', 'no_proxy': ''})
        with mock.patch.dict(os.environ, proxies), \
             mock.patch('proxy.h2_transport.asyncio.open_connection',
                        new=mock.AsyncMock(side_effect=OSError('offline test'))) as dial:
            lane = _HttpLane('kws2.example.org', 1)
            try:
                with self.assertRaises(httpx.ConnectError):
                    await lane.client.get('https://kws2.example.org/api')
                dial.assert_awaited_once()
                self.assertEqual(dial.call_args.args, ('kws2.example.org', 443))
                self.assertEqual(dial.call_args.kwargs['server_hostname'], 'kws2.example.org')
            finally:
                await lane.close()

    async def test_cold_worker_keeps_success_accounting_and_tls_mode(self):
        proxy_config.cfproxy_worker_domains = ['worker.example']
        for secure in (True, False):
            proxy_config.disable_secure = not secure
            ws = mock.Mock(send=mock.AsyncMock())
            with mock.patch.object(bridge.cf_worker_pool, 'get', new=mock.AsyncMock(return_value=None)), \
                 mock.patch.object(bridge.cf_worker_pool, 'available_domains', return_value=['worker.example']), \
                 mock.patch.object(bridge.cf_worker_pool, 'report_success') as success, \
                 mock.patch.object(bridge.RawWebSocket, 'connect', new=mock.AsyncMock(return_value=ws)) as dial, \
                 mock.patch.object(bridge, 'bridge_ws_reencrypt', new=mock.AsyncMock()):
                result = await bridge._cfproxy_worker_fallback(
                    None, None, b'init', 'test', None, 2, False, False, '149.154.167.51')
                self.assertTrue(result)
                self.assertEqual(dial.call_args.kwargs['secure'], secure)
                success.assert_called_once_with('worker.example')

    async def test_cf_front_respects_tls_mode_and_clears_cooldown(self):
        for secure in (True, False):
            proxy_config.disable_secure = not secure
            with mock.patch.object(bridge.balancer, 'get_domains_for_dc', return_value=iter(['front.example'])), \
                 mock.patch.object(bridge.balancer, 'report_success') as success, \
                 mock.patch.object(bridge.balancer, 'update_domain_for_dc', return_value=False), \
                 mock.patch.object(bridge.RawWebSocket, 'connect', new=mock.AsyncMock(return_value=mock.Mock(send=mock.AsyncMock()))) as dial, \
                 mock.patch.object(bridge, 'bridge_ws_reencrypt', new=mock.AsyncMock()):
                self.assertTrue(await bridge._cfproxy_fallback(None, None, b'init', 'test', None, 2, False))
                self.assertEqual(dial.call_args.kwargs['secure'], secure)
                success.assert_called_once_with('front.example')

    async def test_worker_pool_refill_uses_the_same_tls_mode(self):
        for secure in (True, False):
            proxy_config.disable_secure = not secure
            with mock.patch.object(raw_websocket.RawWebSocket, 'connect', new=mock.AsyncMock(return_value=object())) as dial:
                self.assertIsNotNone(await _CfWorkerPool()._connect_one(['worker.example'], '149.154.167.51', 2))
                self.assertEqual(dial.call_args.kwargs['secure'], secure)

    def test_tls_verifies_certificate_chain_with_bundled_roots(self):
        for context in (raw_websocket._ssl_ctx, raw_websocket._ssl_ctx_fronting):
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertGreater(len(context.get_ca_certs()), 0)
        self.assertTrue(raw_websocket._ssl_ctx.check_hostname)


class CliUpgradeTest(unittest.TestCase):
    def setUp(self):
        previous = copy.deepcopy(vars(proxy_config))
        self.addCleanup(lambda: vars(proxy_config).update(previous))
        root = tg_ws_proxy.logging.getLogger()
        self.addCleanup(root.setLevel, root.level)

    def run_cli(self, args):
        with mock.patch.object(sys, 'argv', ['tgws', '--secret', '01' * 16] + args), \
             mock.patch.object(tg_ws_proxy.asyncio, 'run', side_effect=lambda coroutine: coroutine.close()), \
             mock.patch.object(tg_ws_proxy.logging.getLogger(), 'addHandler'):
            tg_ws_proxy.main()

    def test_omitted_dc_option_keeps_defaults_and_tls(self):
        self.run_cli([])
        self.assertEqual(proxy_config.dc_redirects, {2: '149.154.167.220', 4: '149.154.167.220'})
        self.assertFalse(proxy_config.disable_secure)

    def test_bare_dc_option_disables_redirects_even_with_saved_entries(self):
        self.run_cli(['--dc-ip', '2:149.154.167.220', '--dc-ip', '--no-secure'])
        self.assertEqual(proxy_config.dc_redirects, {})
        self.assertTrue(proxy_config.disable_secure)


if __name__ == '__main__':
    unittest.main()
