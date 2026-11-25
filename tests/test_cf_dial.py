import asyncio
import unittest
from unittest import mock

from proxy import cf_dial
from proxy.cf_dial import FRONTS, connect_cf, scheme_memory
from proxy.config import proxy_config
from proxy.raw_websocket import RawWebSocket, WsHandshakeError


class _Ws:
    def __init__(self, name):
        self.name = name
        self.closed = False

    async def close(self):
        self.closed = True


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


class ConnectCfTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        scheme_memory.reset()
        self.addCleanup(scheme_memory.reset)
        self.dials = []
        for patcher in (
            mock.patch.object(cf_dial, 'HEDGE_DELAY', 0.05),
            mock.patch.object(proxy_config, 'disable_secure', False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _network(self, tls, plain):
        """Each of `tls` / `plain` is a result, an exception or 'silent'."""
        async def connect(host, domain, timeout=10.0, path='/apiws', *,
                          sni=None, secure=True):
            self.dials.append(secure)
            outcome = tls if secure else plain
            if outcome == 'silent':
                await asyncio.Future()
            await asyncio.sleep(0)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        return mock.patch.object(RawWebSocket, 'connect', side_effect=connect)

    async def _dial(self, key=FRONTS):
        return await asyncio.wait_for(
            connect_cf(key, 'kws2.front.example', 'kws2.front.example',
                       timeout=10.0), 2)

    async def test_a_network_where_tls_works_never_dials_plain(self):
        ws = _Ws('tls')
        with self._network(tls=ws, plain=_Ws('plain')):
            self.assertIs(await self._dial(), ws)
        self.assertEqual(self.dials, [True])
        self.assertFalse(scheme_memory.prefers_plain(FRONTS))

    async def test_a_silent_tls_handshake_is_overtaken_by_plain(self):
        # Live 2026-11-25: every front timed out over TLS (cut by SNI) and
        # answered 101 over ws:// in the same minute.
        ws = _Ws('plain')
        with self._network(tls='silent', plain=ws):
            self.assertIs(await self._dial(), ws)
            self.assertEqual(self.dials, [True, False])
            self.assertTrue(scheme_memory.prefers_plain(FRONTS))
            # The delay is paid once: the next dial starts with ws://.
            self.dials.clear()
            self.assertIs(await self._dial(), ws)
            self.assertEqual(self.dials, [False])

    async def test_a_reset_tls_handshake_goes_to_plain_without_waiting(self):
        ws = _Ws('plain')
        with mock.patch.object(cf_dial, 'HEDGE_DELAY', 30.0), \
                self._network(tls=ConnectionResetError(), plain=ws):
            self.assertIs(await self._dial(), ws)
        self.assertEqual(self.dials, [True, False])

    async def test_an_http_answer_over_tls_is_final(self):
        # 503 means the edge was reached: the scheme works, the front is busy,
        # and ws:// would be told the same.
        with self._network(tls=WsHandshakeError(503, 'HTTP/1.1 503 x'),
                           plain=_Ws('plain')):
            with self.assertRaises(WsHandshakeError) as caught:
                await self._dial()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(self.dials, [True])
        self.assertFalse(scheme_memory.prefers_plain(FRONTS))

    async def test_a_front_dead_on_both_schemes_reports_the_tls_failure(self):
        with self._network(tls=ConnectionResetError('tls'),
                           plain=ConnectionRefusedError('plain')):
            with self.assertRaises(ConnectionResetError):
                await self._dial()
        self.assertEqual(self.dials, [True, False])

    async def test_an_http_answer_outranks_a_timeout(self):
        # The callers tell a busy front from a dead one by the status code.
        with self._network(tls=asyncio.TimeoutError(),
                           plain=WsHandshakeError(503, 'HTTP/1.1 503 x')):
            with self.assertRaises(WsHandshakeError):
                await self._dial()

    async def test_no_secure_dials_plain_only(self):
        ws = _Ws('plain')
        with mock.patch.object(proxy_config, 'disable_secure', True), \
                self._network(tls=_Ws('tls'), plain=ws):
            self.assertIs(await self._dial(), ws)
        self.assertEqual(self.dials, [False])

    async def test_the_pool_and_a_worker_learn_apart(self):
        with self._network(tls='silent', plain=_Ws('plain')):
            await self._dial(FRONTS)
        self.assertTrue(scheme_memory.prefers_plain(FRONTS))
        self.assertFalse(scheme_memory.prefers_plain('me.workers.dev'))

    async def test_tls_is_asked_first_again_once_the_memory_expires(self):
        clock = _Clock()
        with mock.patch.object(cf_dial.time, 'monotonic', clock.monotonic):
            scheme_memory.remember(FRONTS, False)
            self.assertEqual(scheme_memory.order(FRONTS), [False, True])
            clock.now += cf_dial.PLAIN_MEMORY + 1
            self.assertEqual(scheme_memory.order(FRONTS), [True, False])

    async def test_a_cancelled_dial_leaves_nothing_in_flight(self):
        with self._network(tls='silent', plain='silent'):
            task = asyncio.ensure_future(connect_cf(
                FRONTS, 'kws2.front.example', 'kws2.front.example', timeout=10.0))
            await asyncio.sleep(0.15)
            self.assertEqual(self.dials, [True, False])
            before = len(asyncio.all_tasks())
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await asyncio.sleep(0)
            self.assertEqual(len(asyncio.all_tasks()), before - 3)


if __name__ == '__main__':
    unittest.main()
