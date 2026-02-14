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


def _now() -> float:
    """Monotonic time source for deterministic timeout calculations."""
    return time.monotonic()

def _set_timeout_metadata(
    error: TimeoutError,
    *,
    description: str,
    timeout: float,
    attempt_count: int,
    elapsed: float,
    stage: Optional[str],
) -> None:
    error.description = description
    error.timeout = timeout
    error.attempt_count = attempt_count
    error.elapsed_time = elapsed
    error.stage = stage

def _log_retry_attempt(description: str, attempt: int, stage: Optional[str]) -> None:
    """Emit sampled retry attempt events to action logger if enabled."""
    try:
        from .actionlogger import ACTION_LOGGER

        if not ACTION_LOGGER.is_enabled():
            return
        if not ACTION_LOGGER.should_log_retry_attempt(attempt):
            return

        ACTION_LOGGER.log(
            action="retry_attempt",
            status="info",
            metadata={"description": description},
            attempt=attempt,
            phase=stage or "execute",
            event="retry_attempt",
        )
    except Exception:
        return

def wait_until(
    predicate: Callable[[], T],
    timeout: float,
    interval: float = 0.2,
    description: str = "condition",
    stage: Optional[str] = None,
) -> T:
    """
    Repeatedly runs predicate until it returns a truthy value,
    or until timeout.
    """
    start_time = _now()
    last_exception: Optional[BaseException] = None
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_start",
            description=description,
            metadata={"timeout_s": timeout, "interval_s": interval, "stage": stage},
        )

    while True:
        attempt_count += 1
        elapsed = _now() - start_time
        
        if elapsed >= timeout:
            break
            
        try:
            result = predicate()
            if result:
                if TIMING_LOGGER.is_enabled():
                    elapsed = _now() - start_time
                    TIMING_LOGGER.log(
                        event="wait_success",
                        description=description,
                        status="success",
                        metadata={
                            "attempts": attempt_count,
                            "elapsed_s": round(elapsed, 3),
                            "stage": stage,
                        },
                    )
                return result
        except BaseException as e:
            last_exception = e
        
        time_left = timeout - elapsed
        sleep_time = min(interval, time_left) if time_left > 0 else 0
        if sleep_time > 0:
            time.sleep(sleep_time)

    elapsed = _now() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_timeout",
            description=description,
            status="error",
            metadata={
                "timeout_s": timeout,
                "attempts": attempt_count,
                "elapsed_s": round(elapsed, 3),
                "stage": stage,
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
    
    _set_timeout_metadata(
        error,
        description=description,
        timeout=timeout,
        attempt_count=attempt_count,
        elapsed=elapsed,
        stage=stage,
    )
    raise error


def wait_until_passes(
    func: Callable[..., T],
    timeout: float,
    interval: float = 0.2,
    exceptions: Tuple[type, ...] = (Exception,),
    description: str = "operation",
    *args: Any,
    stage: Optional[str] = None,
    **kwargs: Any,
) -> T:
    """
    Wait until func(*args, **kwargs) succeeds without raising specified exceptions.
    """
    start_time = _now()
    last_exception: Optional[BaseException] = None
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="retry_start",
            description=description,
            metadata={"timeout_s": timeout, "interval_s": interval, "stage": stage},
        )

    while True:
        attempt_count += 1
        _log_retry_attempt(description, attempt_count, stage)
        try:
            result = func(*args, **kwargs)
            if TIMING_LOGGER.is_enabled():
                elapsed = _now() - start_time
                TIMING_LOGGER.log(
                    event="retry_success",
                    description=description,
                    status="success",
                    metadata={
                        "attempts": attempt_count,
                        "elapsed_s": round(elapsed, 3),
                        "stage": stage,
                    },
                )
            return result
        except exceptions as e:
            last_exception = e
            elapsed = _now() - start_time
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
                            "stage": stage,
                        },
                    )
                error = TimeoutError(
                    f"Timed out waiting for {description} after {timeout}s "
                    f"({attempt_count} attempts). "
                    f"Last error: {type(e).__name__}: {e}"
                )
                _set_timeout_metadata(
                    error,
                    description=description,
                    timeout=timeout,
                    attempt_count=attempt_count,
                    elapsed=elapsed,
                    stage=stage,
                )
                raise error from e
            
            sleep_time = min(interval, time_left)
            if TIMING_LOGGER.is_enabled():
                TIMING_LOGGER.log(
                    event="retry_wait",
                    description=description,
                    metadata={
                        "attempt": attempt_count,
                        "sleep_s": round(sleep_time, 3),
                        "stage": stage,
                    },
                )
            time.sleep(sleep_time)


def wait_until_not(
    predicate: Callable[[], Any],
    timeout: float,
    interval: float = 0.2,
    description: str = "condition to become false",
    stage: Optional[str] = None,
) -> None:
    """
    Wait until predicate returns a falsy value.
    """
    start_time = _now()
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_start",
            description=description,
            metadata={"timeout_s": timeout, "interval_s": interval, "stage": stage},
        )

    while True:
        attempt_count += 1
        elapsed = _now() - start_time
        
        if elapsed >= timeout:
            break
            
        try:
            result = predicate()
            if not result:
                if TIMING_LOGGER.is_enabled():
                    elapsed = _now() - start_time
                    TIMING_LOGGER.log(
                        event="wait_success",
                        description=description,
                        status="success",
                        metadata={
                            "attempts": attempt_count,
                            "elapsed_s": round(elapsed, 3),
                            "stage": stage,
                        },
                    )
                return
        except BaseException:
            return
        
        time_left = timeout - elapsed
        sleep_time = min(interval, time_left) if time_left > 0 else 0
        if sleep_time > 0:
            time.sleep(sleep_time)

    elapsed = _now() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_timeout",
            description=description,
            status="error",
            metadata={
                "timeout_s": timeout,
                "attempts": attempt_count,
                "elapsed_s": round(elapsed, 3),
                "stage": stage,
            },
        )
    error = TimeoutError(
        f"Timed out waiting for {description} after {timeout}s "
        f"(condition kept returning truthy)"
    )
    error.original_exception = None
    _set_timeout_metadata(
        error,
        description=description,
        timeout=timeout,
        attempt_count=attempt_count,
        elapsed=elapsed,
        stage=stage,
    )
    raise error


def wait_for_any(
    predicates: List[Callable[[], Any]],
    timeout: float,
    interval: float = 0.2,
    descriptions: Optional[List[str]] = None,
    stage: Optional[str] = None,
) -> int:
    """
    Wait until any of the predicates returns a truthy value.
    Returns the index of the first predicate that succeeded.
    """
    if descriptions is None:
        descriptions = [f"predicate[{i}]" for i in range(len(predicates))]
    
    start_time = _now()
    last_exceptions: List[Optional[BaseException]] = [None] * len(predicates)
    attempt_count = 0

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_any_start",
            description="any predicate",
            metadata={"timeout_s": timeout, "interval_s": interval, "stage": stage},
        )

    while True:
        attempt_count += 1
        elapsed = _now() - start_time
        
        if elapsed >= timeout:
            break
        
        for i, predicate in enumerate(predicates):
            try:
                result = predicate()
                if result:
                    if TIMING_LOGGER.is_enabled():
                        TIMING_LOGGER.log(
                            event="wait_any_success",
                            description=descriptions[i],
                            status="success",
                            metadata={
                                "attempts": attempt_count,
                                "elapsed_s": round(elapsed, 3),
                                "index": i,
                                "stage": stage,
                            },
                        )
                    return i
            except BaseException as e:
                last_exceptions[i] = e
        
        time_left = timeout - elapsed
        sleep_time = min(interval, time_left) if time_left > 0 else 0
        if sleep_time > 0:
            time.sleep(sleep_time)

    elapsed = _now() - start_time
    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="wait_any_timeout",
            description="any predicate",
            status="error",
            metadata={
                "timeout_s": timeout,
                "attempts": attempt_count,
                "elapsed_s": round(elapsed, 3),
                "stage": stage,
            },
        )
    desc_str = ", ".join(descriptions)
    error = TimeoutError(f"Timed out waiting for any of [{desc_str}] after {timeout}s")
    error.original_exception = next((e for e in last_exceptions if e is not None), None)
    error.original_exceptions = last_exceptions
    _set_timeout_metadata(
        error,
        description=f"any of [{desc_str}]",
        timeout=timeout,
        attempt_count=attempt_count,
        elapsed=elapsed,
        stage=stage,
    )
    raise error


def retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    interval: float = 0.5,
    exceptions: Tuple[type, ...] = (Exception,),
    description: str = "operation",
    *args: Any,
    stage: Optional[str] = None,
    **kwargs: Any
) -> T:
    """
    Retry a function up to max_attempts times.
    """
    start_time = _now()
    last_exception: Optional[BaseException] = None

    if TIMING_LOGGER.is_enabled():
        TIMING_LOGGER.log(
            event="retry_start",
            description=description,
            metadata={"max_attempts": max_attempts, "interval_s": interval, "stage": stage},
        )

    for attempt in range(1, max_attempts + 1):
        _log_retry_attempt(description, attempt, stage)
        try:
            result = func(*args, **kwargs)
            if TIMING_LOGGER.is_enabled():
                elapsed = _now() - start_time
                TIMING_LOGGER.log(
                    event="retry_success",
                    description=description,
                    status="success",
                    metadata={
                        "attempts": attempt,
                        "elapsed_s": round(elapsed, 3),
                        "stage": stage,
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
                            "stage": stage,
                        },
                    )
                time.sleep(interval)
            else:
                elapsed = _now() - start_time
                error = TimeoutError(
                    f"Failed {description} after {max_attempts} attempts. "
                    f"Last error: {type(last_exception).__name__}: {last_exception}"
                )
                error.original_exception = last_exception
                _set_timeout_metadata(
                    error,
                    description=description,
                    timeout=elapsed,
                    attempt_count=max_attempts,
                    elapsed=elapsed,
                    stage=stage,
                )
                raise error from e

    elapsed = _now() - start_time
    
    error = TimeoutError(
        f"Failed {description} after {max_attempts} attempts. "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    )
    error.original_exception = last_exception
    _set_timeout_metadata(
        error,
        description=description,
        timeout=elapsed,
        attempt_count=max_attempts,
        elapsed=elapsed,
        stage=stage,
    )
    raise error