import asyncio
import unittest

from ratatosk.core.idle_worker import IdleTrackingMiddleware, IdleWorker


class TestIdleWorkerSuite(unittest.IsolatedAsyncioTestCase):
    async def test_01_idle_gating_dirty_flag_and_cooperative_yield(self) -> None:
        worker = IdleWorker(
            idle_grace_seconds=0.05,
            poll_interval_seconds=0.02,
            max_cpu_load_ratio=100.0,
        )
        runs: list[str] = []

        async def sample_task() -> str:
            runs.append("ran")
            return "ok"

        worker.register(
            "sample",
            sample_task,
            min_interval=0.01,
            max_interval=None,
            dirty_only=True,
            initial_dirty=True,
        )

        # Immediately after activity -> not idle yet
        worker.on_request_start()
        self.assertFalse(worker.is_idle())
        self.assertEqual(await worker.tick_once(), [])

        worker.on_request_end()
        self.assertEqual(await worker.tick_once(), [])

        # Wait past idle_grace_seconds -> runs once and clears dirty flag
        await asyncio.sleep(0.06)
        self.assertTrue(worker.is_idle())
        self.assertEqual(await worker.tick_once(), ["sample"])
        self.assertEqual(len(runs), 1)

        # Subsequent tick without mark_dirty -> no-op
        await asyncio.sleep(0.02)
        self.assertEqual(await worker.tick_once(), [])
        self.assertEqual(len(runs), 1)

        # Marking dirty schedules another idle run
        worker.mark_dirty("sample")
        await asyncio.sleep(0.02)
        self.assertEqual(await worker.tick_once(), ["sample"])
        self.assertEqual(len(runs), 2)

        # Explicit on-demand execution works even when busy
        worker.on_request_start()
        self.assertEqual(await worker.run_task_now("sample"), "ok")
        worker.on_request_end()
        self.assertEqual(len(runs), 3)

    async def test_02_asgi_middleware_tracks_inflight_requests(self) -> None:
        worker = IdleWorker(idle_grace_seconds=0.0, max_cpu_load_ratio=100.0)
        seen_during_request: list[int] = []

        async def dummy_app(scope, receive, send) -> None:
            seen_during_request.append(worker.active_requests)

        mw = IdleTrackingMiddleware(dummy_app, worker=worker)
        await mw({"type": "http"}, None, None)

        self.assertEqual(seen_during_request, [1])
        self.assertEqual(worker.active_requests, 0)


if __name__ == "__main__":
    unittest.main()

