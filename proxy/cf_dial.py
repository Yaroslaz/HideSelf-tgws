"""Dialling Cloudflare with a plain `ws://` stand-in for a cut `wss://`.

Live capture, 2026-11-25, from a Russian ISP: every front of the pool and the
user's own worker timed out on the TLS handshake (the names are cut by SNI),
direct TCP and the kws* WebSocket were closed by address, and Telegram had
nothing at all -- while the very same fronts answered 101 over `ws://` on
port 80 and carried 12.7 MB sessions. The only way to get there was
`--no-secure`, a process-wide flag: someone had to notice, flip it and restart
the proxy, and the client's tuner needed minutes and several restarts to
arrive at it.

So the stand-in is dialled here, per attempt: the usual scheme first, the
other one alongside it once the first has been silent for `HEDGE_DELAY`.
Whichever completes the WebSocket handshake wins and is remembered, so a
network that cuts TLS pays the delay once, not on every connection.

What the stand-in gives away: the front's name travels in the Host header
instead of the SNI -- the same name, readable either way. The payload is the
obfuscated MTProto stream in both cases.
"""
import asyncio
import logging
import time

from typing import Dict, List, Optional, Tuple

from .config import proxy_config
from .raw_websocket import RawWebSocket, WsHandshakeError


log = logging.getLogger('tg-mtproto-proxy')

# How long the first scheme may stay silent before the other one is dialled
# next to it. A TLS handshake with Cloudflare that works at all completes in
# well under a second (setup_ms=672 for three fronts in the capture above); a
# cut one says nothing until the 10s connect timeout.
HEDGE_DELAY = 2.5
# How long a plain win is trusted before TLS is asked first again. Without an
# expiry a network that cut TLS once would stay on `ws://` for the rest of the
# run; with a short one every connection would pay HEDGE_DELAY again.
PLAIN_MEMORY = 1800.0

# The pool fronts share one memory: they are cut together, by the same rule,
# and learning it front by front would cost HEDGE_DELAY twenty times over.
FRONTS = 'cfproxy'


class _SchemeMemory:
    def __init__(self):
        # key -> (secure, when): the scheme that last completed a handshake.
        self._last: Dict[str, Tuple[bool, float]] = {}

    def prefers_plain(self, key: str) -> bool:
        last = self._last.get(key)
        if last is None:
            return False
        secure, when = last
        return not secure and time.monotonic() - when < PLAIN_MEMORY

    def order(self, key: str) -> List[bool]:
        """`secure` flags to dial, the first one right away."""
        return [False, True] if self.prefers_plain(key) else [True, False]

    def remember(self, key: str, secure: bool) -> None:
        was_plain = self.prefers_plain(key)
        self._last[key] = (secure, time.monotonic())
        # Said once per change, not per dial: this is the line that explains
        # why Telegram came back on a network that cuts the TLS names.
        if not secure and not was_plain:
            log.info("CF %s reachable only without TLS, using ws:// first", key)
        elif secure and was_plain:
            log.info("CF %s reachable over TLS again", key)

    def reset(self) -> None:
        self._last.clear()


scheme_memory = _SchemeMemory()


def _close_late(task: 'asyncio.Future') -> None:
    if task.cancelled() or task.exception() is not None:
        return
    asyncio.ensure_future(_quiet_close(task.result()))


async def _quiet_close(ws) -> None:
    try:
        await ws.close()
    except Exception:
        pass


def _worst_first(errors: List[Tuple[bool, BaseException]]) -> BaseException:
    """The failure worth reporting when both schemes failed.

    An HTTP answer beats a timeout: it proves the edge was reached, and the
    callers tell an overloaded front (503) from a dead one by it. Among equals
    the TLS one wins, being the scheme the breakers were written around.
    """
    answered = [exc for _, exc in errors if isinstance(exc, WsHandshakeError)]
    if answered:
        return answered[0]
    for secure, exc in errors:
        if secure:
            return exc
    return errors[0][1]


async def connect_cf(key: str, host: str, domain: str, *, timeout: float,
                     path: str = '/apiws') -> RawWebSocket:
    """Open a WebSocket to a Cloudflare name, over TLS or without it.

    `key` names the memory the outcome goes to (`FRONTS` for the pool, the
    worker's own domain for a worker). With `--no-secure` only `ws://` is
    dialled, as before: that flag is a decision, not a hint.
    """
    if proxy_config.disable_secure:
        return await RawWebSocket.connect(host, domain, timeout=timeout,
                                          path=path, secure=False)

    first_secure, second_secure = scheme_memory.order(key)
    started = time.monotonic()

    def dial(secure: bool, budget: float) -> 'asyncio.Future':
        return asyncio.ensure_future(RawWebSocket.connect(
            host, domain, timeout=budget, path=path, secure=secure))

    tasks: Dict['asyncio.Future', bool] = {dial(first_secure, timeout): first_secure}
    errors: List[Tuple[bool, BaseException]] = []
    winner: Optional['asyncio.Future'] = None
    try:
        first = next(iter(tasks))
        done, _ = await asyncio.wait({first}, timeout=HEDGE_DELAY)
        if first in done:
            exc = first.exception()
            if exc is None:
                winner = first
            elif isinstance(exc, WsHandshakeError):
                # The edge answered over this scheme, so the scheme works and
                # the refusal is about the front itself (503, 404...). The
                # other scheme would be told the same thing.
                raise exc
            else:
                errors.append((first_secure, exc))

        if winner is None:
            # The stand-in gets what is left of the budget, so a hedged dial
            # never outlasts the timeout its caller planned for.
            left = max(1.0, timeout - (time.monotonic() - started))
            tasks[dial(second_secure, left)] = second_secure
            pending = {task for task in tasks if not task.done()}
            while pending and winner is None:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    exc = task.exception()
                    if exc is not None:
                        errors.append((tasks[task], exc))
                    elif winner is None:
                        winner = task
    finally:
        for task in tasks:
            if task is winner:
                continue
            if task.done():
                _close_late(task)
            else:
                task.cancel()
                task.add_done_callback(_close_late)

    if winner is None:
        raise _worst_first(errors)
    scheme_memory.remember(key, tasks[winner])
    return winner.result()
