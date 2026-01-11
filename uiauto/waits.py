# uiauto/waits.py
from __future__ import annotations
import time
from typing import Callable, Optional, TypeVar

from .exceptions import TimeoutError

T = TypeVar("T")


def wait_until(
    predicate: Callable[[], T],
    timeout: float,
    interval: float = 0.2,
    description: str = "condition",
) -> T:
    """
    Repeatedly runs predicate until it returns a truthy value (or any non-exception value),
    or until timeout.
    - If predicate raises, we retry until timeout.
    - If predicate returns False/None, we retry until timeout.
    """
    end = time.time() + timeout
    last_exc: Optional[BaseException] = None

    while time.time() < end:
        try:
            result = predicate()
            if result:
                return result
        except BaseException as e:
            last_exc = e
        time.sleep(interval)

    if last_exc:
        raise TimeoutError(f"Timed out waiting for {description}: {type(last_exc).__name__}: {last_exc}")
    raise TimeoutError(f"Timed out waiting for {description}")
