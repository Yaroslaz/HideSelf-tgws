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
    # A front that answered with an HTTP overload status (503 and friends)
    # sits out only this long, and the answer does not climb the ladder.
    # Live capture, 2026-11-13, from a Russian ISP: every front of the pool
    # landed on Cloudflare HEL, which answered 503 with an empty body to
    # about 85% of WebSocket handshakes -- per attempt, not per zone: the same
    # host gave 101 and 503 back to back, and 6 of 28 Cloudflare addresses
    # tried for one zone in a row answered 101. Benching a front for a minute
    # on such an answer emptied the 20-front pool within seconds ("every front
    # on cooldown" 3356 times in one afternoon) while a retry had the same
    # one-in-six chance as the first dial. The hold only keeps the very next
    # dial of the same fallback on another front.
    OVERLOAD_HOLD = 2.0
    OVERLOAD_STATUSES = frozenset((429, 502, 503, 504))

    def __init__(self):
        self.domains: List[str] = []
        self._dc_to_domain: Dict[int, str] = {}
        self._unavailable_until: Dict[str, float] = {}
        self._failures: Dict[str, int] = {}
        # Until when a front sits out after a real failure. Kept apart from
        # `_unavailable_until`, which also carries the short in-flight hold:
        # a failure that ends an in-flight hold is news, one that lands while
        # the front is already benched is the same outage reported again.
        self._benched_until: Dict[str, float] = {}
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
        self._benched_until = {
            domain: until for domain, until in self._benched_until.items()
            if domain in known
        }
        self._healthy &= known

    def update_domain_for_dc(self, dc_id: int, domain: str) -> bool:
        if self._dc_to_domain.get(dc_id) == domain:
            return False
        
        self._dc_to_domain[dc_id] = domain
        return True

    def get_domains_for_dc(self, dc_id: int, *, reserve_unproven: bool = True) -> Iterator[str]:
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
            if reserve_unproven and domain not in self._healthy:
                self._unavailable_until[domain] = now + self.IN_FLIGHT_HOLD
            yield domain

    def report_success(self, domain: str) -> None:
        self._unavailable_until.pop(domain, None)
        self._benched_until.pop(domain, None)
        self._failures.pop(domain, None)
        self._healthy.add(domain)

    def report_overload(self, domain: str) -> float:
        """Hold a front that refused one attempt with an overload answer.

        Unlike `report_failure` this neither benches the front nor counts a
        failure: the edge answered, so the host is reachable and the zone is
        configured, and the next attempt is as good as the first one.
        """
        now = time.monotonic()
        # Replaces the in-flight hold rather than extending it: the dial it
        # covered is over, and keeping the front out for the rest of those
        # 12s let a burst of concurrent fallbacks drain the pool again. A real
        # bench from an earlier failure is left as it is.
        until = max(self._benched_until.get(domain, 0.0),
                    now + self.OVERLOAD_HOLD)
        self._unavailable_until[domain] = until
        return until - now

    @classmethod
    def is_overload(cls, exc: BaseException) -> bool:
        return getattr(exc, 'status_code', None) in cls.OVERLOAD_STATUSES

    def report_failure(self, domain: str) -> float:
        """Put a failed front on cooldown and say for how long."""
        self._healthy.discard(domain)
        now = time.monotonic()
        # Dials already in flight when the first one failed land here one
        # after another. The front that last worked is exempt from the
        # in-flight hold, so every concurrent fallback dials it at once, and
        # each failure used to double the bench: on 2026-11-13, right after a
        # start, Cloudflare answered 503 to a burst and one front went
        # 60 -> 120 -> 240 -> 480s within the same second, the whole pool was
        # benched for up to ten minutes ("every front on cooldown"), and
        # Telegram had nothing but a blocked direct TCP. Restarting the proxy
        # was the only cure, because it was the only thing that forgot the
        # ladder. Same rule as the CF worker breaker (pool.py).
        benched_until = self._benched_until.get(domain, 0.0)
        if benched_until > now:
            return benched_until - now
        failures = min(self._failures.get(domain, 0) + 1, self.BACKOFF_STEPS)
        self._failures[domain] = failures
        cooldown = min(self.FAILURE_COOLDOWN * (2 ** (failures - 1)),
                       self.MAX_COOLDOWN)
        self._unavailable_until[domain] = now + cooldown
        self._benched_until[domain] = now + cooldown
        return cooldown


balancer = _Balancer()
