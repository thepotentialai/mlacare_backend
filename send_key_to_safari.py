import subprocess, sys, time
from Quartz.CoreGraphics import (
    kCGEventKeyDown,
    kCGEventKeyUp,
    CGEventCreateKeyboardEvent,
    CGEventPostToPid,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift
)

def safari_pid():
    """Retourne le PID de Safari"""
    out = subprocess.check_output(["pgrep", "-x", "Safari"]).strip()
    return int(out.splitlines()[0])

def send_combo(pid, keycode, flags):
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up   = CGEventCreateKeyboardEvent(None, keycode, False)
    if flags:
        CGEventSetFlags(down, flags)
        CGEventSetFlags(up, flags)
    CGEventPostToPid(pid, down)
    CGEventPostToPid(pid, up)

pid = safari_pid()
flags = kCGEventFlagMaskCommand | kCGEventFlagMaskShift
# keycode 16 = Y, ce qui correspond à Cmd+Shift+Y (raccourci de SingleFile)
send_combo(pid, 16, flags)
time.sleep(0.2)