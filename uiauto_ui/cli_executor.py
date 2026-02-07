# uiauto_ui/cli_executor.py
"""
CLI execution layer with threading support.

Provides two executor types:
- InProcessExecutor: Runs CLI in same process (run, inspect)
- SubprocessExecutor: Runs CLI as subprocess (record)

Both emit signals for thread-safe UI updates.
"""

import io
import os
import sys
import subprocess
import contextlib
from datetime import datetime
from typing import Optional, List

from PySide6.QtCore import QThread, Signal, QObject

from .models.command_result import CommandResult
from .models.execution_state import ExecutionState, ExecutionPhase
from .utils.logging import get_logger, log_command_start, log_command_finish, log_exception
from .utils.platform import get_subprocess_env, get_python_executable, get_startupinfo

logger = get_logger(__name__)


class ExecutorSignals(QObject):
    """
    Signals emitted by executors.

    Must be QObject subclass for signal definition.
    Signals are thread-safe and can be connected to UI slots.
    """
    # Emitted when output is received (line by line)
    output_received = Signal(str)

    # Emitted when error output is received
    error_received = Signal(str)

    # Emitted when execution phase changes
    phase_changed = Signal(ExecutionPhase)

    # Emitted when execution completes (success or failure)
    finished = Signal(CommandResult)

    # Emitted on progress (optional, for future use)
    progress = Signal(int, int)  # current, total


class BaseExecutor(QThread):
    """
    Base class for CLI executors.

    Subclasses must implement _execute() method.
    All executors emit the same signals for consistent UI handling.
    """

    def __init__(self, argv: List[str], parent: Optional[QObject] = None):
        super().__init__(parent)
        self.argv = argv
        self.command = argv[0] if argv else "unknown"
        self.signals = ExecutorSignals()

        self._state = ExecutionState()
        self._should_stop = False
        self._started_at: Optional[datetime] = None
        self._finished_at: Optional[datetime] = None

    @property
    def is_cancellable(self) -> bool:
        """Whether this executor supports cancellation."""
        return True

    def request_stop(self) -> None:
        """Request graceful stop of execution."""
        logger.info(f"Stop requested for {self.command}")
        self._should_stop = True
        self.signals.phase_changed.emit(ExecutionPhase.STOPPING)

    def run(self) -> None:
        """
        Thread entry point. Do not call directly - use start().
        """
        self._started_at = datetime.now()
        self._state.start(self.command, self.argv)
        self.signals.phase_changed.emit(ExecutionPhase.RUNNING)

        log_command_start(logger, self.command, self.argv)
        self._log_execution_context()

        try:
            return_code = self._execute()
        except Exception as e:
            log_exception(logger, f"executing {self.command}", e)
            self._emit_error(f"[EXCEPTION] {type(e).__name__}: {e}")
            return_code = 1
            self._state.error(str(e))

        self._finished_at = datetime.now()
        self._state.complete(return_code)

        result = CommandResult(
            command=self.command,
            argv=self.argv,
            return_code=return_code,
            output="\n".join(self._state.output_lines),
            errors="\n".join(self._state.error_lines),
            started_at=self._started_at,
            finished_at=self._finished_at,
            exception=self._state.exception,
        )

        log_command_finish(logger, self.command, return_code, result.duration_seconds)
        self.signals.finished.emit(result)

    def _log_execution_context(self) -> None:
        """Log execution context (cwd, python, env)."""
        env_keys = ["PATH", "PYTHONPATH", "JAVA_HOME", "JDK_HOME", "CLASSPATH", "PYTHONIOENCODING", "PYTHONUTF8"]
        env_snapshot = {key: os.environ.get(key, "") for key in env_keys}
        logger.debug(f"Execution context: pid={os.getpid()} cwd={os.getcwd()}")
        logger.debug(f"Python executable: {sys.executable}")
        logger.debug(f"Environment snapshot: {env_snapshot}")

    def _execute(self) -> int:
        """
        Execute the command. Override in subclasses.

        Returns:
            Exit code (0 = success)
        """
        raise NotImplementedError("Subclasses must implement _execute()")

    def _emit_output(self, text: str) -> None:
        """Emit output signal and track in state."""
        for line in text.splitlines():
            self._state.append_output(line)
            self.signals.output_received.emit(line)

    def _emit_error(self, text: str) -> None:
        """Emit error signal and track in state."""
        for line in text.splitlines():
            self._state.append_error(line)
            self.signals.error_received.emit(line)


class InProcessExecutor(BaseExecutor):
    """
    Executes CLI commands in the same process.

    Best for: run, inspect, validate, list-elements

    Advantages:
    - Direct access to uiauto internals
    - Faster startup
    - Easier debugging

    Disadvantages:
    - Shares memory with UI
    - Cannot capture Ctrl+C separately
    """

    def _execute(self) -> int:
        """Execute CLI in-process with stdout/stderr capture."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Import here to avoid circular imports and startup cost
            from uiauto.cli import main as cli_main

            # Capture stdout/stderr
            with contextlib.redirect_stdout(stdout_capture), \
                 contextlib.redirect_stderr(stderr_capture):
                return_code = cli_main(self.argv)

            # Emit captured output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            if stdout_content:
                self._emit_output(stdout_content)
            if stderr_content:
                self._emit_error(stderr_content)

            return return_code if return_code is not None else 0

        except SystemExit as e:
            # CLI may call sys.exit()
            code = e.code if isinstance(e.code, int) else 1
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            if stdout_content:
                self._emit_output(stdout_content)
            if stderr_content:
                self._emit_error(stderr_content)

            return code

        except KeyboardInterrupt:
            self._emit_output("[Interrupted by user]")
            return -1

        except Exception as e:
            self._emit_error(f"[EXCEPTION] {type(e).__name__}: {e}")
            logger.exception(f"Exception in InProcessExecutor: {e}")
            return 1


class SubprocessExecutor(BaseExecutor):
    """
    Executes CLI commands as a subprocess.

    Best for: record (requires separate process for keyboard hooks)

    Advantages:
    - Isolated from UI process
    - Can be terminated independently
    - Handles Ctrl+C properly for recording

    Disadvantages:
    - Slower startup
    - Encoding issues on Windows
    """

    def __init__(self, argv: List[str], parent: Optional[QObject] = None):
        super().__init__(argv, parent)
        self._process: Optional[subprocess.Popen] = None

    @property
    def is_cancellable(self) -> bool:
        return True

    def request_stop(self) -> None:
        """Terminate the subprocess."""
        super().request_stop()
        if self._process is not None:
            try:
                logger.info("Terminating subprocess...")
                self._process.terminate()
            except (OSError, ProcessLookupError) as e:
                logger.warning(f"Could not terminate process: {e}")

    def _execute(self) -> int:
        """Execute CLI as subprocess with real-time output streaming."""
        cmd = [get_python_executable(), "-m", "uiauto.cli"] + self.argv

        logger.debug(f"Subprocess command: {' '.join(cmd)}")

        env = get_subprocess_env()
        startupinfo = get_startupinfo()
        cwd = os.getcwd()
        env_keys = ["PATH", "PYTHONPATH", "JAVA_HOME", "JDK_HOME", "CLASSPATH", "PYTHONIOENCODING", "PYTHONUTF8"]
        env_snapshot = {key: env.get(key, "") for key in env_keys}
        logger.debug(f"Subprocess context: cwd={cwd}")
        logger.debug(f"Subprocess env snapshot: {env_snapshot}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
                encoding="utf-8",
                errors="replace",  # Replace undecodable chars
                env=env,
                startupinfo=startupinfo,
                cwd=cwd,
            )
            logger.info(f"Subprocess started: pid={self._process.pid}")

            # Stream output line by line
            for line in iter(self._process.stdout.readline, ''):
                if self._should_stop:
                    self._process.terminate()
                    self._emit_output("[Stopped by user]")
                    break

                line = line.rstrip('\n\r')
                if line:
                    self._emit_output(line)

            # Wait for process to complete
            self._process.wait()
            return_code = self._process.returncode

            if return_code is None:
                return_code = -1

            return return_code

        except FileNotFoundError as e:
            self._emit_error(f"[ERROR] Python executable not found: {e}")
            return 1

        except OSError as e:
            self._emit_error(f"[ERROR] Failed to start subprocess: {e}")
            return 1

        except Exception as e:
            self._emit_error(f"[EXCEPTION] {type(e).__name__}: {e}")
            logger.exception(f"Exception in SubprocessExecutor: {e}")
            return 1

        finally:
            self._process = None


def create_executor(
    command: str,
    argv: List[str],
    parent: Optional[QObject] = None
) -> BaseExecutor:
    """
    Factory function to create the appropriate executor.

    Args:
        command: CLI command name
        argv: Full argument list
        parent: Optional Qt parent object

    Returns:
        Executor instance ready to start()
    """
    # Record must run as subprocess for keyboard hooks.
    if command == "record":
        logger.debug(f"Creating SubprocessExecutor for '{command}'")
        return SubprocessExecutor(argv, parent)

    # Run/validate should match CLI subprocess behavior for isolation.
    if command in {"run", "validate"}:
        logger.debug(f"Creating SubprocessExecutor for '{command}'")
        return SubprocessExecutor(argv, parent)

    logger.debug(f"Creating InProcessExecutor for '{command}'")
    return InProcessExecutor(argv, parent)
