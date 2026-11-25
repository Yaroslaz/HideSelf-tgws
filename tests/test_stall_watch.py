import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock
from unittest.mock import AsyncMock, Mock

from proxy import bridge
from proxy.bridge import bridge_ws_reencrypt
from proxy.config import proxy_config
from proxy.stats import stats


def _same():
    return SimpleNamespace(update=lambda data: data)


class StallWatchTest(unittest.IsolatedAsyncioTestCase):
    """Live 2026-11-25: single connections through Cloudflare went silent
    downstream while the client kept asking; Telegram dropped each one only
    after 15-16s and was answered within 80-330ms on the next."""

    def setUp(self):
        for patcher in (
            mock.patch.object(proxy_config, 'stall_timeout', 0.2),
            mock.patch.object(bridge, 'STALL_CHECK_INTERVAL', 0.02),
            mock.patch.object(stats, 'ws_stalled', 0),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.replies = asyncio.Queue()
        self.ws = SimpleNamespace(send=AsyncMock(), send_batch=AsyncMock(),
                                  recv=self.replies.get, close=AsyncMock())
        self.writer = Mock(wait_closed=AsyncMock(), drain=AsyncMock())
        self.ctx = SimpleNamespace(clt_dec=_same(), tg_enc=_same(),
                                   tg_dec=_same(), clt_enc=_same())

    async def asyncSetUp(self):
        self.reader = asyncio.StreamReader()

    def _bridge(self):
        return asyncio.ensure_future(bridge_ws_reencrypt(
            self.reader, self.writer, self.ws, 'stall-test', self.ctx, dc=2))

    async def _ask(self, size=300):
        self.reader.feed_data(b'q' * size)
        await asyncio.sleep(0.01)

    async def _settled(self, task, within):
        done, _ = await asyncio.wait({task}, timeout=within)
        if not done:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        return bool(done)

    async def test_requests_left_unanswered_close_the_session(self):
        task = self._bridge()
        await self._ask()
        await self._ask()
        with self.assertLogs('tg-mtproto-proxy', 'INFO') as logs:
            self.assertTrue(await self._settled(task, 1.0))
        self.assertTrue(any('WS session closed (stalled: no reply' in line
                            for line in logs.output), logs.output)
        self.ws.close.assert_awaited_once()
        self.assertEqual(stats.ws_stalled, 1)

    async def test_a_single_unanswered_packet_is_not_a_stall(self):
        # An acknowledgement after a finished download gets no reply, and the
        # connection then idles by right.
        task = self._bridge()
        await self._ask()
        self.assertFalse(await self._settled(task, 0.5))
        self.assertEqual(stats.ws_stalled, 0)

    async def test_a_session_that_is_answered_stays(self):
        task = self._bridge()
        for _ in range(6):
            await self._ask()
            await self._ask()
            await asyncio.sleep(0.1)
            self.replies.put_nowait(b'reply')
            await asyncio.sleep(0.01)
        self.assertFalse(task.done())
        self.assertFalse(await self._settled(task, 0.1))
        self.assertEqual(stats.ws_stalled, 0)

    async def test_an_upload_waiting_for_its_part_to_arrive_stays(self):
        # A part of a file on a slow uplink can take longer than the timeout
        # before Telegram has anything to acknowledge.
        task = self._bridge()
        for _ in range(4):
            await self._ask(8 * 1024)
        self.assertFalse(await self._settled(task, 0.5))
        self.assertEqual(stats.ws_stalled, 0)

    async def test_zero_switches_the_watch_off(self):
        with mock.patch.object(proxy_config, 'stall_timeout', 0.0):
            task = self._bridge()
            await self._ask()
            await self._ask()
            self.assertFalse(await self._settled(task, 0.5))


if __name__ == '__main__':
    unittest.main()
