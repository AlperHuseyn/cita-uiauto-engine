#!/usr/bin/env python3
import os
import sys

from uiauto import Repository, Session, Resolver, Actions


def main() -> int:
    """
    QtQuickTaskApp için developer-mode E2E otomasyon.
    YAML veya CLI kullanmadan, framework API'si ile çalışır.
    """

    # ===== PATH CONFIG =====
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    OBJECT_MAP = os.path.join(ROOT, "object-maps", "elements.yaml")
    APP_PATH = r"C:\\Users\\alper\\source\\repos\\QtQuickTaskApp-oltan\\out\\build\\x64-Debug\\QtQuickTaskApp.exe"

    USERNAME = "AutomationTest"
    TASK_TEXT = "Test Task - Create and Remove"

    if not os.path.exists(APP_PATH):
        print(f"Uygulama bulunamadı: {APP_PATH}")
        return 1

    # ===== LOAD OBJECT MAP =====
    repo = Repository(OBJECT_MAP)

    # ===== SESSION =====
    session = Session(
        backend=repo.app.backend,
        default_timeout=repo.app.default_timeout,
        polling_interval=repo.app.polling_interval,
    )

    print("Uygulama başlatılıyor...")
    session.start(APP_PATH, wait_for_idle=False)

    resolver = Resolver(session, repo)
    actions = Actions(resolver)

    try:
        # ===== LOGIN =====
        print("Login yapılıyor...")
        actions.wait_for("usernamefield", state="visible")
        actions.type("usernamefield", USERNAME)
        actions.click("loginbutton")

        # ===== CREATE TASK =====
        print("Task oluşturuluyor...")
        actions.wait_for("taskinput", state="visible")
        actions.type("taskinput", TASK_TEXT)
        actions.click("addtaskbutton")

        # ===== REMOVE TASK =====
        print("Task siliniyor...")
        actions.wait_for("removetaskbutton_0", state="visible")
        actions.click("removetaskbutton_0")

        # ===== LOGOUT (CTRL + L) =====
        print("Logout (Ctrl+L)...")
        actions.hotkey("^l")

        # ===== DONE =====
        print("QtQuickTaskApp E2E otomasyonu başarıyla tamamlandı.")
        return 0

    except Exception as e:
        print("\nOtomasyon başarısız oldu!")
        print(e)
        return 2

    finally:
        # ===== CLEANUP =====
        try:
            session.close_main_windows(timeout=3.0)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
