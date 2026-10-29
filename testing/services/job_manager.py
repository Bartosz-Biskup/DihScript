import asyncio
from collections.abc import Awaitable, Callable


class JobManager:
    """Runs background group jobs, at most one at a time.

    ``_busy`` is checked and set synchronously inside ``start``, which runs in
    the event loop thread without awaiting, so check-and-set is atomic and no
    second job can slip in before the first task actually acquires the lock.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._busy = False
        self._tasks: dict[int, asyncio.Task] = {}

    def is_busy(self) -> bool:
        return self._busy

    def start(self, group_id: int, job: Callable[[], Awaitable[None]]) -> bool:
        if self._busy:
            return False
        self._busy = True
        self._tasks[group_id] = asyncio.create_task(self._run(group_id, job))
        return True

    async def _run(self, group_id: int, job: Callable[[], Awaitable[None]]) -> None:
        try:
            async with self._lock:
                await job()
        finally:
            self._tasks.pop(group_id, None)
            self._busy = False
