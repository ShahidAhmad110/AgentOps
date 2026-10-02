"""Setup AgentOps Windows Auto-Start
Ensures AgentOps starts automatically whenever the computer restarts.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
APPDATA = os.getenv("APPDATA")
STARTUP_DIR = Path(APPDATA) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
USERPROFILE = os.getenv("USERPROFILE")
DESKTOP_DIR = Path(USERPROFILE) / "Desktop" if USERPROFILE else None


def setup() -> None:
    # 1. Create run_background.vbs in root
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{ROOT_DIR}"
WshShell.Run "python run_project.py", 0, False
'''
    vbs_file = ROOT_DIR / "run_background.vbs"
    vbs_file.write_text(vbs_content, encoding="utf-8")
    print(f"[AutoStart] Created {vbs_file}")

    # 2. Copy/Create in Windows Startup folder
    if STARTUP_DIR.exists():
        startup_vbs = STARTUP_DIR / "AgentOps_AutoStart.vbs"
        startup_vbs.write_text(vbs_content, encoding="utf-8")
        print(f"[AutoStart] Registered Windows startup file: {startup_vbs}")
    else:
        print(f"[AutoStart] Warning: Startup directory {STARTUP_DIR} not found.")

    # 3. Create Desktop shortcut
    if DESKTOP_DIR and DESKTOP_DIR.exists():
        desktop_bat = DESKTOP_DIR / "Start AgentOps.bat"
        desktop_bat_content = f'''@echo off
title AgentOps
cd /d "{ROOT_DIR}"
python run_project.py
'''
        desktop_bat.write_text(desktop_bat_content, encoding="utf-8")
        print(f"[AutoStart] Created Desktop launcher: {desktop_bat}")


if __name__ == "__main__":
    setup()
