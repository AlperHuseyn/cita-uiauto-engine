# tests/test_waits.py
"""
Tests for wait utilities.
"""

import pytest
import time
from uiauto.waits import (
    wait_until,
    wait_until_passes,
    wait_until_not,
    wait_for_any,
    retry
)
from uiauto.exceptions import TimeoutError


class TestWaitUntil:
    """Tests for wait_until function."""
    
    def test_returns_immediately_when_true(self):
        """Should return immediately when predicate is true."""
        result = wait_until(lambda: True, timeout=5)
        assert result is True
    
    def test_returns_truthy_value(self):
        """Should return the truthy value from predicate."""
        result = wait_until(lambda: "hello", timeout=5)
        assert result == "hello"
    
    def test_waits_for_condition(self):
        """Should wait until condition becomes true."""
        start = time.time()
        counter = {"value": 0}
        
        def predicate():
            counter["value"] += 1
            return counter["value"] >= 3
        
        result = wait_until(predicate, timeout=5, interval=0.1)
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed >= 0.2  # At least 2 intervals
        assert elapsed < 1.0   # But not too long
    
    def test_timeout_raises_error(self):
        """Should raise TimeoutError when timeout expires."""
        with pytest.raises(TimeoutError) as exc_info:
            wait_until(lambda: False, timeout=0.3, interval=0.1)
        
        assert "Timed out" in str(exc_info.value)
        assert exc_info.value.timeout == 0.3
    
    def test_preserves_exception(self):
        """Should preserve the last exception in TimeoutError."""
        def failing_predicate():
            raise ValueError("test error")
        
        with pytest.raises(TimeoutError) as exc_info:
            wait_until(failing_predicate, timeout=0.3, interval=0.1)
        
        assert exc_info.value.original_exception is not None
        assert isinstance(exc_info.value.original_exception, ValueError)
        assert "test error" in str(exc_info.value.original_exception)


class TestWaitUntilPasses:
    """Tests for wait_until_passes function."""
    
    def test_returns_immediately_on_success(self):
        """Should return immediately when function succeeds."""
        result = wait_until_passes(
            lambda: "success",
            timeout=5,
            description="test"
        )
        assert result == "success"
    
    def test_retries_on_exception(self):
        """Should retry when function raises exception."""
        counter = {"value": 0}
        
        def flaky_func():
            counter["value"] += 1
            if counter["value"] < 3:
                raise ValueError("not yet")
            return "success"
        
        result = wait_until_passes(
            flaky_func,
            timeout=5,
            interval=0.1,
            exceptions=(ValueError,),
            description="flaky function"
        )
        
        assert result == "success"
        assert counter["value"] == 3
    
    def test_timeout_with_exception_info(self):
        """Should include exception info in TimeoutError."""
        def always_fails():
            raise RuntimeError("always fails")
        
        with pytest.raises(TimeoutError) as exc_info:
            wait_until_passes(
                always_fails,
                timeout=0.3,
                interval=0.1,
                exceptions=(RuntimeError,),
                description="failing operation"
            )
        
        error = exc_info.value
        assert error.original_exception is not None
        assert isinstance(error.original_exception, RuntimeError)
        assert error.attempt_count >= 1
        assert "failing operation" in str(error)
    
    def test_with_args_and_kwargs(self):
        """Should pass args and kwargs to function."""
        def add(a, b, multiplier=1):
            return (a + b) * multiplier
        
        result = wait_until_passes(
            add,
            timeout=5,
            description="addition",
            a=2, b=3,  # positional args
            multiplier=2  # keyword arg
        )
        
        assert result == 10
    
    def test_only_catches_specified_exceptions(self):
        """Should only catch specified exception types."""
        def raises_type_error():
            raise TypeError("wrong type")
        
        # TypeError is not in the exceptions tuple, so it should propagate
        with pytest.raises(TypeError):
            wait_until_passes(
                raises_type_error,
                timeout=1,
                exceptions=(ValueError,),  # Only ValueError
                description="test"
            )


class TestWaitUntilNot:
    """Tests for wait_until_not function."""
    
    def test_returns_when_falsy(self):
        """Should return when predicate becomes falsy."""
        counter = {"value": 3}
        
        def predicate():
            counter["value"] -= 1
            return counter["value"] > 0
        
        wait_until_not(predicate, timeout=5, interval=0.1)
        assert counter["value"] == 0
    
    def test_timeout_when_always_truthy(self):
        """Should timeout when predicate stays truthy."""
        with pytest.raises(TimeoutError):
            wait_until_not(lambda: True, timeout=0.3, interval=0.1)


class TestWaitForAny:
    """Tests for wait_for_any function."""
    
    def test_returns_first_truthy_index(self):
        """Should return index of first truthy predicate."""
        predicates = [
            lambda: False,
            lambda: True,
            lambda: False,
        ]
        
        result = wait_for_any(predicates, timeout=5)
        assert result == 1
    
    def test_handles_delayed_success(self):
        """Should handle predicates that become true later."""
        counter = {"value": 0}
        
        def delayed_predicate():
            counter["value"] += 1
            return counter["value"] >= 3
        
        predicates = [
            lambda: False,
            delayed_predicate,
        ]
        
        result = wait_for_any(predicates, timeout=5, interval=0.1)
        assert result == 1
    
    def test_timeout_when_none_succeed(self):
        """Should timeout when no predicate succeeds."""
        predicates = [lambda: False, lambda: False]
        
        with pytest.raises(TimeoutError) as exc_info:
            wait_for_any(predicates, timeout=0.3, interval=0.1)
        
        assert hasattr(exc_info.value, 'original_exceptions')


class TestRetry:
    """Tests for retry function."""
    
    def test_succeeds_on_first_attempt(self):
        """Should return immediately on first success."""
        result = retry(lambda: "success", max_attempts=3)
        assert result == "success"
    
    def test_retries_on_failure(self):
        """Should retry up to max_attempts times."""
        counter = {"value": 0}
        
        def flaky():
            counter["value"] += 1
            if counter["value"] < 2:
                raise ValueError("not yet")
            return "success"
        
        result = retry(flaky, max_attempts=3, interval=0.1)
        assert result == "success"
        assert counter["value"] == 2
    
    def test_raises_after_max_attempts(self):
        """Should raise after max_attempts failures."""
        counter = {"value": 0}
        
        def always_fails():
            counter["value"] += 1
            raise ValueError("always fails")
        
        with pytest.raises(TimeoutError) as exc_info:
            retry(always_fails, max_attempts=3, interval=0.1)
        
        assert counter["value"] == 3
        assert exc_info.value.attempt_count == 3


class TestTimeoutErrorAttributes:
    """Tests for TimeoutError attributes."""
    
    def test_get_root_cause(self):
        """Should get root cause from nested exceptions."""
        inner = ValueError("root cause")
        
        error = TimeoutError("outer error")
        error.original_exception = inner
        
        root = error.get_root_cause()
        assert root is inner
        assert str(root) == "root cause"
    
    def test_get_traceback_str(self):
        """Should get formatted traceback string."""
        try:
            raise ValueError("test error")
        except ValueError as e:
            error = TimeoutError("timeout")
            error.original_exception = e
            
            tb_str = error.get_traceback_str()
            assert "ValueError" in tb_str
            assert "test error" in tb_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
