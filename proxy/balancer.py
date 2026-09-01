import random
import time

from collections import Counter

from typing import Dict, Iterator, List, Set


class _Balancer:
    # A front that just failed is held out of rotation instead of being
    # re-dialled by the very next fallback. Without this the pool is swept in
    # full on every client fallback: ~19 domains x 10s connect timeout, per
    # connection, forever. Measured on a dead pool that came to 18.7 dials per
    # fallback and >2000 outbound connections a minute, which on a TUN stack
    # burns two ephemeral loopback ports each and exhausts the range.
    FAILURE_COOLDOWN = 60.0
    # Doubling per further failure, capped: a pool that is simply gone should
    # cost a handful of probes an hour, not thousands.
    MAX_COOLDOWN = 600.0
    # Doublings kept on record. Four already carry 60s past MAX_COOLDOWN, and
    # the clamp stops a front that fails for hours from growing the shift into
    # a thousand-bit integer.
    BACKOFF_STEPS = 8
    # Held while a dial to an unproven front is still in flight, so
    # concurrent fallbacks spread over the pool instead of all waiting on the
    # same dead host. Covers the 10s connect timeout in `_cfproxy_fallback`;
    # it expires by itself, so a cancelled task cannot strand a domain.
    # A front that last worked is exempt: holding it would push every
    # concurrent fallback onto untested hosts and past MAX_ATTEMPTS, which
    # cost 95% of the successful CF connections in a replay of the incident.
    IN_FLIGHT_HOLD = 12.0
    # Fronts a single fallback may try before giving up and letting the next
    # method (CF worker, plain TCP) take over. The pool still gets
    # explored, across fallbacks rather than within one.
    MAX_ATTEMPTS = 3

    def __init__(self):
        self.domains: List[str] = []
        self._dc_to_domain: Dict[int, str] = {}
        self._unavailable_until: Dict[str, float] = {}
        self._failures: Dict[str, int] = {}
        self._healthy: Set[str] = set()

    def update_domains_list(self, domains_list: List[str]) -> None:
        if Counter(self.domains) == Counter(domains_list):
            return
        
        self.domains = domains_list[:]

        self._dc_to_domain = {
            dc_id: random.choice(self.domains)
            for dc_id in (1, 2, 3, 4, 5, 203)
        }

        # The pool is refreshed hourly; without pruning, the breaker state of
        # every domain ever seen would stay behind it.
        known = set(self.domains)
        self._unavailable_until = {
            domain: until for domain, until in self._unavailable_until.items()
            if domain in known
        }
        self._failures = {
            domain: count for domain, count in self._failures.items()
            if domain in known
        }
        self._healthy &= known

    def update_domain_for_dc(self, dc_id: int, domain: str) -> bool:
        if self._dc_to_domain.get(dc_id) == domain:
            return False
        
        self._dc_to_domain[dc_id] = domain
        return True

    def get_domains_for_dc(self, dc_id: int) -> Iterator[str]:
        current_domain = self._dc_to_domain.get(dc_id)

        # Proven fronts before unproven ones: MAX_ATTEMPTS is small, and a
        # host that just worked should not lose its place to a shuffle.
        rest = [d for d in self.domains if d != current_domain]
        random.shuffle(rest)
        healthy = [d for d in rest if d in self._healthy]
        unproven = [d for d in rest if d not in self._healthy]

        candidates: List[str] = []
        if current_domain is not None:
            candidates.append(current_domain)
        candidates.extend(healthy)
        candidates.extend(unproven)

        attempts = 0
        for domain in candidates:
            if attempts >= self.MAX_ATTEMPTS:
                return
            # Re-read the clock on every iteration: the caller awaits a dial
            # between yields, so a timestamp taken once would be seconds
            # stale by the time the later candidates are checked.
            now = time.monotonic()
            if self._unavailable_until.get(domain, 0.0) > now:
                continue
            attempts += 1
            if domain not in self._healthy:
                self._unavailable_until[domain] = now + self.IN_FLIGHT_HOLD
            yield domain

    def report_success(self, domain: str) -> None:
        self._unavailable_until.pop(domain, None)
        self._failures.pop(domain, None)
        self._healthy.add(domain)

    def report_failure(self, domain: str) -> float:
        """Put a failed front on cooldown and say for how long."""
        self._healthy.discard(domain)
        failures = min(self._failures.get(domain, 0) + 1, self.BACKOFF_STEPS)
        self._failures[domain] = failures
        cooldown = min(self.FAILURE_COOLDOWN * (2 ** (failures - 1)),
                       self.MAX_COOLDOWN)
        self._unavailable_until[domain] = time.monotonic() + cooldown
        return cooldown


balancer = _Balancer()
