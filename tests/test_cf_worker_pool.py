import asyncio
import unittest
from unittest import mock

from proxy import pool as pool_module
from proxy.config import proxy_config
from proxy.pool import _CfWorkerPool
from proxy.raw_websocket import WsHandshakeError


class _Clock:
    """Stand-in for the module's `time`, so cooldowns can be stepped by hand."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


class _FakeTransport:
    def is_closing(self):
        return False


class _FakeWriter:
    def __init__(self):
        self.transport = _FakeTransport()


class _FakeWs:
    def __init__(self):
        self._closed = False
        self.writer = _FakeWriter()

    async def close(self):
        self._closed = True


async def _settle():
    """Let the refill tasks the pool spawned run to completion."""
    for _ in range(4):
        await asyncio.sleep(0)
        pending = [t for t in asyncio.all_tasks()
                   if t is not asyncio.current_task() and not t.done()]
        if not pending:
            return
        await asyncio.gather(*pending, return_exceptions=True)


class CfWorkerPoolTest(unittest.TestCase):
    DC = 2
    DST = '149.154.167.51'

    def setUp(self):
        self.clock = _Clock()
        patcher = mock.patch.object(pool_module, 'time', self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)

        previous = proxy_config.pool_size
        proxy_config.pool_size = 4
        self.addCleanup(setattr, proxy_config, 'pool_size', previous)

        self.pool = _CfWorkerPool()
        self.workers = ['w1.example', 'w2.example']
        self.dials = 0

    def _serving(self):
        async def _connect_one(worker_domains, fallback_dst, dc):
            self.dials += 1
            available = self.pool.available_domains(worker_domains)
            if not available:
                return None
            return _FakeWs(), available[0]
        return _connect_one

    def _refusing(self, exc=None):
        async def _connect_one(worker_domains, fallback_dst, dc):
            self.dials += 1
            for domain in self.pool.available_domains(worker_domains):
                self.pool.report_failure(domain, exc or TimeoutError())
            return None
        return _connect_one

    def _get(self, connect_one):
        """One `get` plus whatever refill it scheduled."""
        async def _run():
            self.pool._connect_one = connect_one
            result = await self.pool.get(self.DC, self.DST, self.workers)
            await _settle()
            return result
        return asyncio.run(_run())

    # --- the trap: a hit needed a full pool, filling needed a hit ---------

    def test_a_miss_schedules_a_refill(self):
        self.assertIsNone(self._get(self._serving()))
        self.assertEqual(len(self.pool._idle[self.DC]), 1)

    def test_the_pool_serves_the_connection_after_a_miss(self):
        self._get(self._serving())
        pooled = self._get(self._serving())
        self.assertIsNotNone(pooled)

    def test_an_expired_batch_does_not_strand_the_pool(self):
        self._get(self._serving())
        self.clock.now += self.pool.WS_POOL_MAX_AGE + 1
        self.assertIsNone(self._get(self._serving()))   # stale one dropped
        self.assertIsNotNone(self._get(self._serving()))

    # --- refilling on a miss must not become its own dial storm ----------

    def test_a_down_worker_backs_the_refill_off(self):
        self._get(self._refusing())
        self.assertGreater(self.pool._refill_after[self.DC], self.clock.now)

    def test_the_backed_off_refill_does_not_dial_again(self):
        self._get(self._refusing())
        dials = self.dials
        self._get(self._refusing())
        self.assertEqual(self.dials, dials)

    def test_a_success_elsewhere_does_not_lift_this_dcs_backoff(self):
        # A worker's rest is per domain and every DC shares it, so a hit on
        # another DC clears it. The per-DC backoff is what still holds this
        # one back from dialling a pool that just failed for it.
        self._get(self._refusing())
        dials = self.dials
        for worker in self.workers:
            self.pool.report_success(worker)
        self._get(self._refusing())
        self.assertEqual(self.dials, dials)

    def test_the_refill_returns_after_the_backoff_expires(self):
        self._get(self._refusing())
        dials = self.dials
        self.clock.now += self.pool.REFILL_BACKOFF_MAX + 1
        self._get(self._serving())
        self.assertGreater(self.dials, dials)

    def test_resting_workers_are_not_counted_as_a_refill_failure(self):
        for worker in self.workers:
            self.pool.report_failure(worker, TimeoutError())

        async def _run():
            self.pool._connect_one = self._serving()
            await self.pool._refill(self.DC, self.DST, self.workers)
        asyncio.run(_run())

        self.assertEqual(self.dials, 0)
        self.assertNotIn(self.DC, self.pool._refill_after)

    # --- the breaker that sat behind a bare `return` ----------------------

    def test_a_failing_worker_is_set_aside(self):
        cooldown = self.pool.report_failure(self.workers[0], TimeoutError())
        self.assertEqual(cooldown, self.pool.FAILURE_COOLDOWN)
        self.assertEqual(self.pool.available_domains(self.workers),
                         [self.workers[1]])

    def test_the_worker_comes_back_when_its_rest_is_over(self):
        cooldown = self.pool.report_failure(self.workers[0], TimeoutError())
        self.clock.now += cooldown + 1
        self.assertEqual(sorted(self.pool.available_domains(self.workers)),
                         sorted(self.workers))

    def test_a_quota_refusal_rests_far_longer_than_a_timeout(self):
        quota = WsHandshakeError(429, '429 Too Many Requests')
        # Captured rather than silenced: hitting the daily quota is the one
        # failure here the operator has to be told about.
        with self.assertLogs(pool_module.log, 'WARNING') as logs:
            quota_rest = self.pool.report_failure(self.workers[0], quota)
        self.assertIn('request limit', logs.output[0])
        self.assertGreater(
            quota_rest,
            self.pool.report_failure(self.workers[1], TimeoutError()))

    def test_success_clears_the_rest(self):
        self.pool.report_failure(self.workers[0], TimeoutError())
        self.pool.report_success(self.workers[0])
        self.assertIn(self.workers[0], self.pool.available_domains(self.workers))

    def test_the_cooldown_ladder_is_bounded(self):
        ladder = [self.pool.report_failure(self.workers[0], TimeoutError())
                  for _ in range(40)]
        self.assertEqual(ladder[0], self.pool.FAILURE_COOLDOWN)
        self.assertLessEqual(max(ladder), self.pool.COOLDOWN_MAX)
        self.assertLessEqual(self.pool._failures[self.workers[0]],
                             self.pool.BACKOFF_STEPS)

    def test_reset_clears_the_breaker(self):
        self._get(self._refusing())
        self.pool.reset()
        self.assertEqual(self.pool._unavailable_until, {})
        self.assertEqual(self.pool._failures, {})
        self.assertEqual(self.pool._refill_failures, {})
        self.assertEqual(self.pool._refill_after, {})


if __name__ == '__main__':
    unittest.main()
