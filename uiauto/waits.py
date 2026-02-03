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
    last_exception: Optional[BaseException] = None

    while time.time() < end:
        try:
            result = predicate()
            if result:
                return result
        except BaseException as e:
            last_exception = e
        time.sleep(interval)

    if last_exception:
        error = TimeoutError(
            f"Timed out waiting for {description} after {timeout}s: "
            f"{type(last_exception).__name__}: {last_exception}"
        )
        error.original_exception = last_exception
        error.description = description
        error.timeout = timeout
        raise error
    
    error = TimeoutError(f"Timed out waiting for {description} after {timeout}s")
    error.original_exception = None
    error.description = description
    error.timeout = timeout
    raise error

def wait_until_passes(
    func: Callable[..., T],
    timeout: float,
    interval: float = 0.2,
    exceptions: Tuple[type, ...] = (Exception,),
    description: str = "operation",
    *args,
    **kwargs
) -> T:
    """
    Wait until func(*args, **kwargs) succeeds without raising specified exceptions.
    
    This function repeatedly calls the provided function until it completes
    without raising one of the specified exception types, or until the timeout
    is reached. The original exception is preserved for debugging.
    
    @param func Function to call
    @param timeout Maximum time to wait in seconds
    @param interval Time between retry attempts in seconds
    @param exceptions Tuple of exception types to catch and retry
    @param description Human-readable description for error messages
    @param args Positional arguments to pass to func
    @param kwargs Keyword arguments to pass to func
    @return The return value of func when it succeeds
    @throws TimeoutError if func keeps raising exceptions until timeout
    
    @code
    # Example: Wait for element to be clickable
    def click_element():
        element = find_element("button")
        element.click()
        return element
    
    result = wait_until_passes(
        click_element,
        timeout=10,
        interval=0.5,
        exceptions=(ElementNotFoundError, ElementNotVisibleError),
        description="clicking submit button"
    )
    @endcode
    
    @code
    # Example: With arguments
    def set_text(element_name, text):
        element = find_element(element_name)
        element.set_text(text)
        return element
    
    result = wait_until_passes(
        set_text,
        timeout=5,
        exceptions=(Exception,),
        description="setting username",
        "username_field",  # positional arg
        text="admin"       # keyword arg
    )
    @endcode
    """
    start_time = time.time()
    last_exception: Optional[BaseException] = None
    attempt_count = 0

    while True:
        attempt_count += 1
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            elapsed = time.time() - start_time
            time_left = timeout - elapsed
            
            if time_left <= 0:
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
            time.sleep(sleep_time)


def wait_until_not(
    predicate: Callable[[], Any],
    timeout: float,
    interval: float = 0.2,
    description: str = "condition to become false",
) -> None:
    """
    Wait until predicate returns a falsy value.
    
    Useful for waiting until an element disappears, a loading spinner
    is gone, or a modal is closed.
    
    @param predicate Callable that should eventually return falsy value
    @param timeout Maximum time to wait in seconds
    @param interval Time between checks in seconds
    @param description Human-readable description for error messages
    @throws TimeoutError if predicate keeps returning truthy until timeout
    
    @code
    # Wait for loading spinner to disappear
    wait_until_not(
        lambda: spinner.is_visible(),
        timeout=30,
        description="loading spinner to disappear"
    )
    @endcode
    """
    end_time = time.time() + timeout
    last_exception: Optional[BaseException] = None

    while time.time() < end_time:
        try:
            result = predicate()
            if not result:
                return
        except BaseException as e:
            last_exception = e
            return
        time.sleep(interval)

    error = TimeoutError(
        f"Timed out waiting for {description} after {timeout}s "
        f"(condition kept returning truthy)"
    )
    error.original_exception = last_exception
    error.description = description
    error.timeout = timeout
    raise error


def wait_for_any(
    predicates: list,
    timeout: float,
    interval: float = 0.2,
    descriptions: Optional[list] = None,
) -> int:
    """
    Wait until any of the predicates returns a truthy value.
    
    Returns the index of the first predicate that succeeded.
    Useful for handling multiple possible UI states.
    
    @param predicates List of callables to check
    @param timeout Maximum time to wait in seconds
    @param interval Time between checks in seconds
    @param descriptions Optional list of descriptions for each predicate
    @return Index of the first predicate that returned truthy
    @throws TimeoutError if no predicate succeeds within timeout
    
    @code
    # Wait for either success message or error dialog
    result = wait_for_any(
        [
            lambda: success_label.is_visible(),
            lambda: error_dialog.exists(),
        ],
        timeout=10,
        descriptions=["success message", "error dialog"]
    )
    
    if result == 0:
        print("Operation succeeded")
    else:
        print("Error occurred")
    @endcode
    """
    if descriptions is None:
        descriptions = [f"predicate[{i}]" for i in range(len(predicates))]
    
    end_time = time.time() + timeout
    last_exceptions: list = [None] * len(predicates)

    while time.time() < end_time:
        for i, predicate in enumerate(predicates):
            try:
                result = predicate()
                if result:
                    return i
            except BaseException as e:
                last_exceptions[i] = e
        time.sleep(interval)

    desc_str = ", ".join(descriptions)
    error = TimeoutError(
        f"Timed out waiting for any of [{desc_str}] after {timeout}s"
    )
    error.original_exceptions = last_exceptions
    error.descriptions = descriptions
    error.timeout = timeout
    raise error


def retry(
    func: Callable[..., T],
    max_attempts: int = 3,
    interval: float = 0.5,
    exceptions: Tuple[type, ...] = (Exception,),
    description: str = "operation",
    *args,
    **kwargs
) -> T:
    """
    Retry a function up to max_attempts times.
    
    Unlike wait_until_passes which uses a timeout, this function
    limits by number of attempts.
    
    @param func Function to call
    @param max_attempts Maximum number of attempts
    @param interval Time between retry attempts in seconds
    @param exceptions Tuple of exception types to catch and retry
    @param description Human-readable description for error messages
    @param args Positional arguments to pass to func
    @param kwargs Keyword arguments to pass to func
    @return The return value of func when it succeeds
    @throws The last exception if all attempts fail
    
    @code
    # Retry clicking a button up to 3 times
    result = retry(
        lambda: button.click(),
        max_attempts=3,
        interval=0.5,
        description="clicking submit button"
    )
    @endcode
    """
    last_exception: Optional[BaseException] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts:
                time.sleep(interval)

    error = TimeoutError(
        f"Failed {description} after {max_attempts} attempts. "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    )
    error.original_exception = last_exception
    error.description = description
    error.attempt_count = max_attempts
    raise error
