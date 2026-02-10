# uiauto/waits.py
"""
@file waits.py
@brief Wait and retry utilities for UI automation.
"""

from __future__ import annotations

import time
from typing import Any, Callable, List, Optional, Tuple, TypeVar

from .exceptions import TimeoutError
from .timinglogger import TimingLogger

TIMING_LOGGER = TimingLogger()

T = TypeVar("T")


def wait_until(
    predicate: Callable[[], T],
    timeout: float,
    interval: float = 0.2,
    description: str = "condition",
) -> T:
    """
    Repeatedly runs predicate until it returns a truthy value,
    or until timeout.
    """
    start_time = time.time()
    last_exception: Optional[BaseException] = None
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_start",
            description=description,
            metadata={"timeout_s": timeout, "interval_s": interval},
        )

    while True:
        attempt_count += 1
        elapsed = time.time() - start_time
        
        if elapsed >= timeout:
            break
            
        try:
            result = predicate()
            if result:
                if TIMING_LOGGER.is_enabled():
                    elapsed = time.time() - start_time
                    TIMING_LOGGER.log(
                        event="wait_success",
                        description=description,
                        status="success",
                        metadata={
                            "attempts": attempt_count,
                            "elapsed_s": round(elapsed, 3),
                        },
                    )
                return result
        except BaseException as e:
            last_exception = e
        
        time_left = timeout - elapsed
        sleep_time = min(interval, time_left) if time_left > 0 else 0
        if sleep_time > 0:
            time.sleep(sleep_time)

    elapsed = time.time() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_timeout",
            description=description,
            status="error",
            metadata={
                "timeout_s": timeout,
                "attempts": attempt_count,
                "elapsed_s": round(elapsed, 3),
            },
        )
    
    if last_exception:
        error = TimeoutError(
            f"Timed out waiting for {description} after {timeout}s: "
            f"{type(last_exception).__name__}: {last_exception}"
        )
        error.original_exception = last_exception
    else:
        error = TimeoutError(
            f"Timed out waiting for {description} after {timeout}s "
            f"(condition kept returning falsy)"
        )
        error.original_exception = None
    
    error.description = description
    error.timeout = timeout
    error.attempt_count = attempt_count
    error.elapsed_time = elapsed
    raise error


def wait_until_passes(
    func: Callable[..., T],
    timeout: float,
    interval: float = 0.2,
    exceptions: Tuple[type, ...] = (Exception,),
    description: str = "operation",
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Wait until func(*args, **kwargs) succeeds without raising specified exceptions.
    """
    start_time = time.time()
    last_exception: Optional[BaseException] = None
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="retry_start",
            description=description,
            metadata={"timeout_s": timeout, "interval_s": interval},
        )

    while True:
        attempt_count += 1
        try:
            result = func(*args, **kwargs)
            if TIMING_LOGGER.is_enabled():
                elapsed = time.time() - start_time
                TIMING_LOGGER.log(
                    event="retry_success",
                    description=description,
                    status="success",
                    metadata={
                        "attempts": attempt_count,
                        "elapsed_s": round(elapsed, 3),
                    },
                )
            return result
        except exceptions as e:
            last_exception = e
            elapsed = time.time() - start_time
            time_left = timeout - elapsed
            
            if time_left <= 0:
                if TIMING_LOGGER.is_enabled():
                    TIMING_LOGGER.log(
                        event="retry_timeout",
                        description=description,
                        status="error",
                        metadata={
                            "attempts": attempt_count,
                            "elapsed_s": round(elapsed, 3),
                        },
                    )
                error = TimeoutError(
                    f"Timed out waiting for {description} after {timeout}s "
                    f"({attempt_count} attempts). "
                    f"Last error: {type(e).__name__}: {e}"
                )
                error.original_exception = last_exception
                error.description = description
                error.timeout = timeout
                error.attempt_count = attempt_count
                error.elapsed_time = elapsed
                raise error
            
            sleep_time = min(interval, time_left)
            if TIMING_LOGGER.is_enabled():
                TIMING_LOGGER.log(
                    event="retry_wait",
                    description=description,
                    metadata={
                        "attempt": attempt_count,
                        "sleep_s": round(sleep_time, 3),
                    },
                )
            time.sleep(sleep_time)


def wait_until_not(
    predicate: Callable[[], Any],
    timeout: float,
    interval: float = 0.2,
    description: str = "condition to become false",
) -> None:
    """
    Wait until predicate returns a falsy value.
    """
    start_time = time.time()
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_start",
            description=description,
            metadata={"timeout_s": timeout, "interval_s": interval},
        )

    while True:
        attempt_count += 1
        elapsed = time.time() - start_time
        
        if elapsed >= timeout:
            break
            
        try:
            result = predicate()
            if not result:
                if TIMING_LOGGER.is_enabled():
                    elapsed = time.time() - start_time
                    TIMING_LOGGER.log(
                        event="wait_success",
                        description=description,
                        status="success",
                        metadata={
                            "attempts": attempt_count,
                            "elapsed_s": round(elapsed, 3),
                        },
                    )
                return
        except BaseException:
            return
        
        time_left = timeout - elapsed
        sleep_time = min(interval, time_left) if time_left > 0 else 0
        if sleep_time > 0:
            time.sleep(sleep_time)

    elapsed = time.time() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_timeout",
            description=description,
            status="error",
            metadata={
                "timeout_s": timeout,
                "attempts": attempt_count,
                "elapsed_s": round(elapsed, 3),
            },
        )
    error = TimeoutError(
        f"Timed out waiting for {description} after {timeout}s "
        f"(condition kept returning truthy)"
    )
    error.original_exception = None
    error.description = description
    error.timeout = timeout
    error.attempt_count = attempt_count
    error.elapsed_time = elapsed
    raise error


def wait_for_any(
    predicates: List[Callable[[], Any]],
    timeout: float,
    interval: float = 0.2,
    descriptions: Optional[List[str]] = None,
) -> int:
    """
    Wait until any of the predicates returns a truthy value.
    Returns the index of the first predicate that succeeded.
    """
    if descriptions is None:
        descriptions = [f"predicate[{i}]" for i in range(len(predicates))]
    
    start_time = time.time()
    last_exceptions: List[Optional[BaseException]] = [None] * len(predicates)
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_any_start",
            description="any predicate",
            metadata={"timeout_s": timeout, "interval_s": interval},
        )

    while True:
        attempt_count += 1
        elapsed = time.time() - start_time
        
        if elapsed >= timeout:
            break
        
        for i, predicate in enumerate(predicates):
            try:
                result = predicate()
                if result:
                    if TIMING_LOGGER.is_enabled():
                        TIMING_LOGGER.log(
                            event="wait_any_success",
                            description=descriptions[i] if descriptions else f"predicate[{i}]",
                            status="success",
                            metadata={
                                "attempts": attempt_count,
                                "elapsed_s": round(elapsed, 3),
                                "index": i,
                            },
                        )
                    return i
            except BaseException as e:
                last_exceptions[i] = e
        
        time_left = timeout - elapsed
        sleep_time = min(interval, time_left) if time_left > 0 else 0
        if sleep_time > 0:
            time.sleep(sleep_time)

    elapsed = time.time() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_any_timeout",
            description="any predicate",
            status="error",
            metadata={
                "timeout_s": timeout,
                "attempts": attempt_count,
                "elapsed_s": round(elapsed, 3),
            },
        )
    desc_str = ", ".join(descriptions)
    error = TimeoutError(
        f"Timed out waiting for any of [{desc_str}] after {timeout}s"
    )
    error.original_exception = next((e for e in last_exceptions if e is not None), None)
    error.description = f"any of [{desc_str}]"
    error.timeout = timeout
    error.attempt_count = attempt_count
    error.elapsed_time = elapsed
    raise error


def retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    interval: float = 0.5,
    exceptions: Tuple[type, ...] = (Exception,),
    description: str = "operation",
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Retry a function up to max_attempts times.
    """
    start_time = time.time()
    last_exception: Optional[BaseException] = None

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="retry_start",
            description=description,
            metadata={"max_attempts": max_attempts, "interval_s": interval},
        )

    for attempt in range(1, max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            if TIMING_LOGGER.is_enabled():
                elapsed = time.time() - start_time
                TIMING_LOGGER.log(
                    event="retry_success",
                    description=description,
                    status="success",
                    metadata={
                        "attempts": attempt,
                        "elapsed_s": round(elapsed, 3),
                    },
                )
            return result
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts:
                if TIMING_LOGGER.is_enabled():
                    TIMING_LOGGER.log(
                        event="retry_wait",
                        description=description,
                        metadata={
                            "attempt": attempt,
                            "sleep_s": round(interval, 3),
                        },
                    )
                time.sleep(interval)

    elapsed = time.time() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="retry_failed",
            description=description,
            status="error",
            metadata={
                "attempts": max_attempts,
                "elapsed_s": round(elapsed, 3),
            },
        )
    error = TimeoutError(
        f"Failed {description} after {max_attempts} attempts. "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    )
    error.original_exception = last_exception
    error.description = description
    error.attempt_count = max_attempts
    error.elapsed_time = elapsed
    raise error