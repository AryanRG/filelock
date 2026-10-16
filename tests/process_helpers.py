from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from multiprocessing.process import BaseProcess

#: Stays under the suite's per-test timeout so a wedged worker still surfaces as the hang it is.
_REAP_DEADLINE: Final[int] = 5


@contextmanager
def cleanup_processes(processes: list[BaseProcess]) -> Generator[None]:
    """Reap every process on the way out, whatever the block did."""
    try:
        yield
    finally:
        for process in processes:
            # Terminating an unstarted process raises over the assertion that escaped before it started.
            if process.pid is not None:
                process.terminate()
                process.join(timeout=_REAP_DEADLINE)
                if process.is_alive():  # pragma: no cover  # SIGTERM only loses this race on a saturated runner
                    process.kill()
                    process.join(timeout=_REAP_DEADLINE)
            # Left open, the finalizer runs during whichever test the collector lands in, as an unraisable exception.
            process.close()


def call_within(call: Callable[[], object], seconds: float) -> tuple[bool, BaseException | None]:
    """Run *call* on a daemon thread and report whether it returned within *seconds* and what it raised."""
    raised: list[BaseException] = []

    def run() -> None:
        try:
            call()
        except Exception as error:  # handed to the caller, which asserts on it
            raised.append(error)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(seconds)
    return not thread.is_alive(), next(iter(raised), None)


__all__ = ["call_within", "cleanup_processes"]
