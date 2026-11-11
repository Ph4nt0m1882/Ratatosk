import asyncio
import contextlib
import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

IdleCallback = Callable[[], Awaitable[Any]]


@dataclass
class IdleTask:
    name: str
    callback: IdleCallback
    min_interval: float = 30.0
    max_interval: float | None = 3600.0
    dirty_only: bool = True
    dirty: bool = True
    last_run_at: float = 0.0
    running: bool = False

    def should_run(self, now: float) -> bool:
        if self.running:
            return False
        elapsed = now - self.last_run_at
        if self.last_run_at > 0.0 and elapsed < self.min_interval:
            return False
        if not self.dirty_only:
            return True
        if self.dirty:
            return True
        return self.max_interval is not None and (
            self.last_run_at == 0.0 or elapsed >= self.max_interval
        )


class IdleWorker:
    """Runs registered maintenance tasks only when the server is idle and CPU is calm."""

    def __init__(
        self,
        idle_grace_seconds: float = 15.0,
        poll_interval_seconds: float = 5.0,
        max_cpu_load_ratio: float = 0.75,
    ) -> None:
        self.idle_grace_seconds = idle_grace_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_cpu_load_ratio = max_cpu_load_ratio

        self.active_requests = 0
        self.last_activity_at = time.monotonic()
        self._tasks: dict[str, IdleTask] = {}
        self._runner: asyncio.Task[None] | None = None

    def on_request_start(self) -> None:
        self.active_requests += 1
        self.last_activity_at = time.monotonic()

    def on_request_end(self) -> None:
        self.active_requests = max(0, self.active_requests - 1)
        self.last_activity_at = time.monotonic()

    def _is_cpu_calm(self) -> bool:
        try:
            load_1m = os.getloadavg()[0]
            cores = max(1, os.cpu_count() or 1)
            return (load_1m / cores) <= self.max_cpu_load_ratio
        except AttributeError, OSError:
            return True

    def is_idle(self) -> bool:
        if self.active_requests > 0:
            return False
        if (time.monotonic() - self.last_activity_at) < self.idle_grace_seconds:
            return False
        return self._is_cpu_calm()

    def register(
        self,
        name: str,
        callback: IdleCallback,
        *,
        min_interval: float = 30.0,
        max_interval: float | None = 3600.0,
        dirty_only: bool = True,
        initial_dirty: bool = True,
    ) -> None:
        self._tasks[name] = IdleTask(
            name=name,
            callback=callback,
            min_interval=min_interval,
            max_interval=max_interval,
            dirty_only=dirty_only,
            dirty=initial_dirty,
        )

    def mark_dirty(self, name: str) -> None:
        task = self._tasks.get(name)
        if task is not None:
            task.dirty = True

    async def run_task_now(self, name: str) -> Any:
        """Execute a registered task immediately (e.g. admin refresh/purge)."""
        task = self._tasks.get(name)
        if task is None:
            raise KeyError(f"Unknown idle task: {name!r}")

        task.running = True
        task.dirty = False
        try:
            result = await task.callback()
            task.last_run_at = time.monotonic()
            return result
        except Exception:
            task.dirty = True
            raise
        finally:
            task.running = False

    async def tick_once(self) -> list[str]:
        """Run one pass of eligible tasks while the server remains idle."""
        executed: list[str] = []
        if not self.is_idle():
            return executed

        for task in list(self._tasks.values()):
            if not self.is_idle():
                break
            now = time.monotonic()
            if not task.should_run(now):
                continue

            try:
                await self.run_task_now(task.name)
                executed.append(task.name)
            except Exception:
                logger.exception("Background idle task '%s' failed", task.name)

        return executed

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.poll_interval_seconds)
            await self.tick_once()

    def start(self) -> None:
        if self._runner is None or self._runner.done():
            self._runner = asyncio.create_task(
                self._loop(), name="ratatosk-idle-worker"
            )

    async def stop(self) -> None:
        if self._runner is not None and not self._runner.done():
            self._runner.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._runner
        self._runner = None


class IdleTrackingMiddleware:
    """Pure ASGI middleware tracking in-flight HTTP/SSE/WebSocket activity."""

    def __init__(self, app: ASGIApp, worker: IdleWorker) -> None:
        self.app = app
        self.worker = worker

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        self.worker.on_request_start()
        try:
            await self.app(scope, receive, send)
        finally:
            self.worker.on_request_end()


idle_worker = IdleWorker()
