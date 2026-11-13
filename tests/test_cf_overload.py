import asyncio
import unittest
from unittest import mock

from proxy import balancer as balancer_module
from proxy import bridge
from proxy.balancer import _Balancer
from proxy.raw_websocket import WsHandshakeError


def _busy():
    return WsHandshakeError(503, 'HTTP/1.1 503 Service Unavailable')


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


class BalancerOverloadTest(unittest.TestCase):
    def setUp(self):
        self.clock = _Clock()
        patcher = mock.patch.object(balancer_module, 'time', self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.balancer = _Balancer()
        self.domains = [f'front{i:02d}.example' for i in range(20)]
        self.balancer.update_domains_list(self.domains)

    def test_overload_status_is_recognised(self):
        self.assertTrue(_Balancer.is_overload(_busy()))
        self.assertTrue(_Balancer.is_overload(WsHandshakeError(429, 'x')))
        self.assertFalse(_Balancer.is_overload(WsHandshakeError(404, 'x')))
        self.assertFalse(_Balancer.is_overload(ConnectionResetError()))

    def test_a_busy_front_is_back_in_seconds_without_climbing_the_ladder(self):
        # Live 2026-11-13: Cloudflare HEL answered 503 to ~85% of handshakes,
        # per attempt; a one-minute bench per 503 emptied the pool.
        domain = self.domains[0]
        for _ in range(5):
            hold = self.balancer.report_overload(domain)
            self.assertEqual(hold, self.balancer.OVERLOAD_HOLD)
            self.clock.now += hold + 0.1
        self.assertNotIn(domain, self.balancer._failures)
        self.assertNotIn(domain, self.balancer._benched_until)

    def test_a_busy_answer_cuts_the_in_flight_hold_short(self):
        dialled = list(self.balancer.get_domains_for_dc(2))
        for domain in dialled:
            self.balancer.report_overload(domain)
        self.clock.now += self.balancer.OVERLOAD_HOLD + 0.1
        offered = set()
        for _ in range(len(self.domains)):
            offered.update(self.balancer.get_domains_for_dc(2))
        self.assertTrue(set(dialled) <= offered)

    def test_a_busy_answer_does_not_shorten_a_real_bench(self):
        domain = self.domains[0]
        bench = self.balancer.report_failure(domain)
        self.assertEqual(self.balancer.report_overload(domain), bench)

    def test_a_pool_answering_busy_never_runs_dry(self):
        # The same burst that used to end in "every front on cooldown".
        for _ in range(200):
            batch = list(self.balancer.get_domains_for_dc(2))
            self.assertTrue(batch, 'pool ran dry')
            for domain in batch:
                self.balancer.report_overload(domain)
            self.clock.now += 0.4


class _Ws:
    def __init__(self, name):
        self.name = name
        self.closed = False
        self.sent = []

    async def send(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True


class CfFallbackRoundsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.balancer = _Balancer()
        self.balancer.update_domains_list([f'front{i:02d}.example' for i in range(20)])
        for patcher in (
            mock.patch.object(bridge, 'balancer', self.balancer),
            mock.patch.object(bridge, 'bridge_ws_reencrypt', mock.AsyncMock()),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.dials = []

    def _connect(self, answers):
        """`answers` maps a dial number to a result; the rest answer 503."""
        async def connect(host, domain, timeout=10.0, secure=True, **_):
            self.dials.append(domain)
            outcome = answers.get(len(self.dials))
            await asyncio.sleep(0.01 * (len(self.dials) % 3))
            if outcome is None:
                raise _busy()
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        return mock.patch.object(bridge.RawWebSocket, 'connect', side_effect=connect)

    async def _fallback(self):
        return await bridge._cfproxy_fallback(None, None, b'init', 'test', None,
                                              dc=2, is_media=False)

    async def test_busy_fronts_are_retried_until_one_answers(self):
        ws = _Ws('winner')
        with self._connect({7: ws}):
            self.assertTrue(await self._fallback())
        self.assertGreaterEqual(len(self.dials), 7)
        self.assertLessEqual(len(self.dials), bridge.CF_OVERLOAD_ATTEMPTS)
        self.assertEqual(ws.sent, [b'init'])
        self.assertEqual(self.balancer._failures, {})

    async def test_retries_stop_at_the_attempt_budget(self):
        with self._connect({}):
            self.assertFalse(await self._fallback())
        self.assertEqual(len(self.dials), bridge.CF_OVERLOAD_ATTEMPTS)

    async def test_a_down_front_still_hands_over_to_the_next_method(self):
        with self._connect({1: ConnectionResetError(), 2: ConnectionResetError(),
                            3: ConnectionResetError()}):
            self.assertFalse(await self._fallback())
        self.assertEqual(len(self.dials), bridge.CF_RACE_WIDTH)
        self.assertEqual(len(self.balancer._failures), bridge.CF_RACE_WIDTH)

    async def test_the_losers_of_a_race_are_closed(self):
        # Two fronts answer 101 in the same tick: one carries the session,
        # the other must not be left open on Cloudflare.
        sockets = [_Ws('first'), _Ws('second'), _Ws('third')]

        async def connect(host, domain, **_):
            self.dials.append(domain)
            return sockets[len(self.dials) - 1]

        with mock.patch.object(bridge.RawWebSocket, 'connect', side_effect=connect):
            self.assertTrue(await self._fallback())
        await asyncio.sleep(0.05)
        self.assertEqual(sum(not ws.closed for ws in sockets), 1)
        self.assertEqual(sum(bool(ws.sent) for ws in sockets), 1)

    async def test_a_slow_front_is_cancelled_once_another_answers(self):
        winner = _Ws('winner')
        slow_cancelled = asyncio.Event()

        async def connect(host, domain, **_):
            self.dials.append(domain)
            if len(self.dials) == 1:
                try:
                    await asyncio.sleep(30)
                except asyncio.CancelledError:
                    slow_cancelled.set()
                    raise
            return winner

        with mock.patch.object(bridge.RawWebSocket, 'connect', side_effect=connect):
            self.assertTrue(await asyncio.wait_for(self._fallback(), 2))
        await asyncio.sleep(0)
        self.assertTrue(slow_cancelled.is_set())


if __name__ == '__main__':
    unittest.main()
