# uiauto_qtquick/session.py
from __future__ import annotations
import os
import time
import logging
from typing import Any, Dict, Optional

from pywinauto.application import Application
from pywinauto import Desktop

from uiauto_core.interfaces import ISession
from uiauto_core.waits import wait_until


class QtQuickSession(ISession):
    """
    Owns the pywinauto Application and provides window acquisition utilities.
    """

    def __init__(
        self,
        backend: str = "uia",
        default_timeout: float = 10.0,
        polling_interval: float = 0.2,
        logger: Optional[logging.Logger] = None,
    ):
        self.backend = backend
        self.default_timeout = float(default_timeout)
        self.polling_interval = float(polling_interval)
        self.log = logger or logging.getLogger("uiauto")
        self.app: Optional[Application] = None
        self._desktop = Desktop(backend=self.backend)
        self._started_pid: Optional[int] = None

    def start(self, app_path: str, wait_for_idle: bool = False, cmd_line: Optional[str] = None) -> int:
        if not os.path.exists(app_path):
            raise FileNotFoundError(app_path)

        self.log.info("Starting app: %s", app_path)
        self.app = Application(backend=self.backend)

        if cmd_line:
            # cmd_line includes path + args
            self.app = self.app.start(cmd_line, wait_for_idle=wait_for_idle)
        else:
            self.app = self.app.start(app_path, wait_for_idle=wait_for_idle)

        # pywinauto sets .process on Application
        self._started_pid = self.app.process
        self.log.info("Started PID=%s", self._started_pid)
        return self._started_pid

    def connect(self, **kwargs: Any) -> None:
        """
        Connect to an existing application by pid/handle/path/title etc.
        Common: connect(process=1234) or connect(handle=0x....)
        """
        self.log.info("Connecting to app with: %s", kwargs)
        self.app = Application(backend=self.backend).connect(**kwargs)
        try:
            self._started_pid = self.app.process
        except Exception:
            self._started_pid = None

    def desktop_window(self, **kwargs: Any):
        """
        Get a top-level window via Desktop() search. Useful fallback.
        Example: desktop_window(title_re=".*Notepad.*")
        """
        return self._desktop.window(**kwargs)

    def app_window(self, **kwargs: Any):
        """
        Get a window via Application() if connected/started.
        """
        if not self.app:
            raise RuntimeError("Session not started/connected.")
        return self.app.window(**kwargs)

    def close(self) -> None:
        """
        Close application gracefully (implements ISession.close).
        Alias for close_main_windows with default timeout.
        """
        self.close_main_windows(timeout=5.0)

    def close_main_windows(self, timeout: float = 5.0) -> None:
        """
        Attempts graceful close of all top windows of the started PID (if known).
        """
        pid = self._started_pid
        if not pid:
            return

        try:
            wins = self._desktop.windows(process=pid)
        except Exception:
            wins = []

        for w in wins:
            try:
                w.close()
            except Exception:
                pass

        # wait a bit for process to exit
        def _no_windows():
            try:
                return len(self._desktop.windows(process=pid)) == 0
            except Exception:
                return True

        try:
            wait_until(_no_windows, timeout=timeout, interval=self.polling_interval, description="windows to close")
        except Exception:
            # best effort
            pass

    def kill(self) -> None:
        if self.app:
            try:
                self.app.kill()
            except Exception:
                pass

    def sleep_brief(self, seconds: float) -> None:
        # Only used internally when absolutely needed.
        time.sleep(seconds)
