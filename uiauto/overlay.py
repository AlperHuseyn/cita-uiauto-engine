# uiauto/overlay.py
from __future__ import annotations

import ctypes
import multiprocessing as mp
import time
from ctypes import wintypes

# Ensure missing wintypes exist (Python 3.13 safety)
if not hasattr(wintypes, "HCURSOR"):
    wintypes.HCURSOR = wintypes.HANDLE
if not hasattr(wintypes, "HICON"):
    wintypes.HICON = wintypes.HANDLE
if not hasattr(wintypes, "HBRUSH"):
    wintypes.HBRUSH = wintypes.HANDLE
if not hasattr(wintypes, "HINSTANCE"):
    wintypes.HINSTANCE = wintypes.HANDLE
if not hasattr(wintypes, "COLORREF"):
    wintypes.COLORREF = wintypes.DWORD

# Win32 constants
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000

SW_SHOW = 5

WM_DESTROY = 0x0002
WM_QUIT = 0x0012

DIB_RGB_COLORS = 0
BI_RGB = 0

AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
ULW_ALPHA = 0x00000002

# Load Win32
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# ---------------------------------------------------------
# 64-bit Safe Signatures (critical)
# ---------------------------------------------------------

user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = ctypes.c_ssize_t

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

user32.PeekMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL

user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = wintypes.LPARAM

user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostQuitMessage.restype = None

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC

gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.c_void_p,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP

user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND,
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(wintypes.SIZE),
    wintypes.HDC,
    ctypes.POINTER(wintypes.POINT),
    wintypes.COLORREF,
    ctypes.c_void_p,
    wintypes.DWORD,
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

SetProcessDPIAware = user32.SetProcessDPIAware


# ---------------------------------------------------------
# Structures
# ---------------------------------------------------------

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", wintypes.BYTE),
        ("BlendFlags", wintypes.BYTE),
        ("SourceConstantAlpha", wintypes.BYTE),
        ("AlphaFormat", wintypes.BYTE),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


# ---------------------------------------------------------
# Overlay Process
# ---------------------------------------------------------

def _overlay_process(queue: mp.Queue):
    try:
        SetProcessDPIAware()
    except Exception:
        pass

    hInstance = kernel32.GetModuleHandleW(None)

    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    class WNDCLASS(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HCURSOR),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    quit_flag = False

    @WNDPROC
    def WndProc(hwnd, msg, wParam, lParam):
        nonlocal quit_flag
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            quit_flag = True
            return 0
        return user32.DefWindowProcW(hwnd, msg, wParam, lParam)

    className = "UIAutoOverlayWindow"

    wc = WNDCLASS()
    wc.style = 0
    wc.lpfnWndProc = WndProc
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = hInstance
    wc.hIcon = None
    wc.hCursor = None
    wc.hbrBackground = None
    wc.lpszMenuName = None
    wc.lpszClassName = className

    user32.RegisterClassW(ctypes.byref(wc))

    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)

    hwnd = user32.CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW,
        className,
        None,
        WS_POPUP,
        0,
        0,
        width,
        height,
        None,
        None,
        hInstance,
        None,
    )

    user32.ShowWindow(hwnd, SW_SHOW)

    screen_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    bmi.bmiHeader.biSizeImage = width * height * 4

    bits = ctypes.c_void_p()
    hbitmap = gdi32.CreateDIBSection(
        mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0
    )
    old_bitmap = gdi32.SelectObject(mem_dc, hbitmap)

    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

    pt_dst = wintypes.POINT(0, 0)
    size = wintypes.SIZE(width, height)
    pt_src = wintypes.POINT(0, 0)

    current_rect = None
    current_color = (0, 255, 0)
    rect_persist_until = 0.0

    def _clear_buffer():
        ctypes.memset(bits.value, 0, width * height * 4)

    def _draw_rect(rect, color_rgb, thickness=3):
        left, top, right, bottom = rect
        left = max(0, min(width - 1, int(left)))
        right = max(0, min(width - 1, int(right)))
        top = max(0, min(height - 1, int(top)))
        bottom = max(0, min(height - 1, int(bottom)))

        if right <= left or bottom <= top:
            return

        b, g, r = int(color_rgb[2]), int(color_rgb[1]), int(color_rgb[0])
        stride = width * 4
        base = bits.value

        def set_px(x, y):
            off = base + y * stride + x * 4
            ctypes.c_ubyte.from_address(off).value = b
            ctypes.c_ubyte.from_address(off + 1).value = g
            ctypes.c_ubyte.from_address(off + 2).value = r
            ctypes.c_ubyte.from_address(off + 3).value = 255

        t = max(1, int(thickness))

        for dy in range(t):
            for x in range(left, right):
                set_px(x, top + dy)
                set_px(x, bottom - 1 - dy)

        for dx in range(t):
            for y in range(top, bottom):
                set_px(left + dx, y)
                set_px(right - 1 - dx, y)

    def _present():
        user32.UpdateLayeredWindow(
            hwnd,
            screen_dc,
            ctypes.byref(pt_dst),
            ctypes.byref(size),
            mem_dc,
            ctypes.byref(pt_src),
            0,
            ctypes.byref(blend),
            ULW_ALPHA,
        )

    _clear_buffer()
    _present()

    msg = wintypes.MSG()

    try:
        while True:
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == WM_QUIT:
                    return
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
                if quit_flag:
                    return

            try:
                cmd = queue.get_nowait()
            except Exception:
                cmd = None

            now = time.time()
            dirty = False

            if cmd:
                ctype = cmd.get("type")

                if ctype == "QUIT":
                    user32.PostQuitMessage(0)
                    return
                elif ctype == "HOVER":
                    current_rect = cmd.get("rect")
                    current_color = (0, 120, 255)
                    rect_persist_until = now + 0.05
                    dirty = True
                elif ctype == "CLICK":
                    current_rect = cmd.get("rect")
                    current_color = (0, 255, 0)
                    rect_persist_until = now + 0.4
                    dirty = True
                elif ctype == "TYPE":
                    current_rect = cmd.get("rect")
                    current_color = (255, 165, 0)
                    rect_persist_until = now + 1.0
                    dirty = True
                elif ctype == "ERROR":
                    current_rect = cmd.get("rect")
                    current_color = (255, 0, 0)
                    rect_persist_until = now + 0.6
                    dirty = True

            if current_rect and now > rect_persist_until:
                current_rect = None
                dirty = True

            if dirty:
                _clear_buffer()
                if current_rect:
                    _draw_rect(current_rect, current_color, 3)
                _present()

            time.sleep(0.01)

    finally:
        gdi32.SelectObject(mem_dc, old_bitmap)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(None, screen_dc)


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

class OverlayController:
    def __init__(self):
        try:
            mp.set_start_method("spawn", force=True)
        except Exception:
            pass

        self.queue = mp.Queue()
        self.process = mp.Process(
            target=_overlay_process,
            args=(self.queue,),
            daemon=True,
        )

    def start(self):
        if not self.process.is_alive():
            self.process.start()

    def stop(self):
        if self.process.is_alive():
            self.queue.put({"type": "QUIT"})
            self.process.join(timeout=1)

    def hover(self, rect):
        self.queue.put({"type": "HOVER", "rect": rect})

    def click(self, rect):
        self.queue.put({"type": "CLICK", "rect": rect})

    def typing(self, rect):
        self.queue.put({"type": "TYPE", "rect": rect})

    def error(self, rect):
        self.queue.put({"type": "ERROR", "rect": rect})
