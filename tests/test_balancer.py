import unittest
from unittest import mock

from proxy import balancer as balancer_module
from proxy.balancer import _Balancer


class _Clock:
    """Stand-in for the module's `time`, so cooldowns can be stepped by hand."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


class BalancerBreakerTest(unittest.TestCase):
    def setUp(self):
        self.clock = _Clock()
        patcher = mock.patch.object(balancer_module, 'time', self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.balancer = _Balancer()
        self.domains = [f'front{i:02d}.example' for i in range(10)]
        self.balancer.update_domains_list(self.domains)

    def test_one_fallback_tries_at_most_max_attempts(self):
        self.assertEqual(
            len(list(self.balancer.get_domains_for_dc(2))),
            self.balancer.MAX_ATTEMPTS,
        )

    def test_failed_front_is_skipped_until_its_cooldown_expires(self):
        failed = next(self.balancer.get_domains_for_dc(2))
        cooldown = self.balancer.report_failure(failed)
        self.assertEqual(cooldown, self.balancer.FAILURE_COOLDOWN)

        self.clock.now += cooldown - 1
        self.assertNotIn(failed, self._sweep_whole_pool(2))

        self.clock.now += 2
        self.assertIn(failed, self._sweep_whole_pool(2))

    def test_cooldown_doubles_per_failure_and_is_capped(self):
        domain = self.domains[0]
        ladder = [self.balancer.report_failure(domain) for _ in range(8)]
        self.assertEqual(ladder[:4], [60.0, 120.0, 240.0, 480.0])
        self.assertTrue(all(step == self.balancer.MAX_COOLDOWN for step in ladder[4:]))

    def test_failure_counter_stays_bounded(self):
        domain = self.domains[0]
        for _ in range(200):
            self.balancer.report_failure(domain)
        self.assertLessEqual(
            self.balancer._failures[domain], self.balancer.BACKOFF_STEPS)

    def test_success_clears_the_cooldown(self):
        domain = self.domains[0]
        self.balancer.report_failure(domain)
        self.balancer.report_success(domain)
        self.assertIn(domain, self._sweep_whole_pool(2))

    def test_in_flight_front_is_not_handed_to_a_concurrent_fallback(self):
        # An unproven front is held for the length of its dial, so parallel
        # fallbacks spread over the pool instead of stacking on one host.
        in_flight = list(self.balancer.get_domains_for_dc(2))
        self.clock.now += 1
        concurrent = self._sweep_whole_pool(2)
        self.assertTrue(set(in_flight).isdisjoint(concurrent))

    def test_the_in_flight_hold_expires_on_its_own(self):
        # Nothing reports the outcome here, standing in for a cancelled task:
        # the front has to come back without anyone releasing it.
        in_flight = list(self.balancer.get_domains_for_dc(2))
        self.clock.now += self.balancer.IN_FLIGHT_HOLD + 1
        self.assertTrue(set(in_flight).issubset(self._sweep_whole_pool(2)))

    def test_a_working_front_is_never_held(self):
        # Holding it would push every concurrent fallback onto untested hosts
        # and past MAX_ATTEMPTS, losing connections the front could have served.
        domain = self.domains[0]
        self.balancer.report_success(domain)
        self.balancer.update_domain_for_dc(2, domain)
        for _ in range(5):
            self.assertEqual(next(self.balancer.get_domains_for_dc(2)), domain)

    def test_a_working_front_outranks_unproven_ones(self):
        healthy = self.domains[7]
        self.balancer.report_success(healthy)
        self.balancer.update_domain_for_dc(2, self.domains[0])
        self.assertIn(healthy, list(self.balancer.get_domains_for_dc(2)))

    def test_a_dead_pool_stops_being_dialled_at_all(self):
        for _ in range(len(self.domains)):
            for domain in self.balancer.get_domains_for_dc(2):
                self.balancer.report_failure(domain)
        self.assertEqual(list(self.balancer.get_domains_for_dc(2)), [])

    def test_refreshing_the_pool_drops_state_for_departed_domains(self):
        self.balancer.report_failure(self.domains[0])
        self.balancer.report_success(self.domains[1])
        self.balancer.update_domains_list(['other.example', 'another.example'])
        self.assertEqual(self.balancer._unavailable_until, {})
        self.assertEqual(self.balancer._failures, {})
        self.assertEqual(self.balancer._healthy, set())

    def _sweep_whole_pool(self, dc_id):
        """Every front the balancer would offer, ignoring MAX_ATTEMPTS."""
        seen = []
        for _ in range(len(self.domains)):
            for domain in self.balancer.get_domains_for_dc(dc_id):
                if domain not in seen:
                    seen.append(domain)
        return seen


if __name__ == '__main__':
    unittest.main()
