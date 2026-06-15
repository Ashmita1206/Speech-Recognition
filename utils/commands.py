"""
Command Detection & Execution Module — Linux Voice Assistant
=============================================================
Detects user intent from transcribed text and maps it to
Linux system commands.  Dangerous commands require explicit
confirmation before execution.

Safety rules:
  • shutdown, reboot, delete, format, system-update → BLOCKED
    until the caller provides a confirmation token.
  • All commands are executed via subprocess (not os.system)
    for better security and output capture.
"""

import os
import re
import uuid
import subprocess
from datetime import datetime


# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------
# Each entry: pattern (regex), intent name, linux command, dangerous flag,
#             human-readable description
# ---------------------------------------------------------------------------

COMMAND_REGISTRY = [
    # --- Browser / Web ---
    {
        "patterns": [
            r"\bopen\b.*\bbrowser\b",
            r"\blaunch\b.*\bbrowser\b",
            r"\bopen\b.*\bgoogle\b",
            r"\bopen\b.*\bchrome\b",
            r"\bopen\b.*\bfirefox\b",
            r"\bgo\b.*\bonline\b",
            r"\bsearch\b.*\bweb\b",
        ],
        "intent": "open_browser",
        "command": "xdg-open https://google.com",
        "dangerous": False,
        "description": "Opening web browser",
    },

    # --- Terminal ---
    {
        "patterns": [
            r"\bopen\b.*\bterminal\b",
            r"\blaunch\b.*\bterminal\b",
            r"\bopen\b.*\bconsole\b",
            r"\bopen\b.*\bshell\b",
        ],
        "intent": "open_terminal",
        "command": "gnome-terminal",
        "dangerous": False,
        "description": "Opening terminal",
    },

    # --- File Manager ---
    {
        "patterns": [
            r"\bopen\b.*\bfile\s*manager\b",
            r"\bopen\b.*\bfiles\b",
            r"\bopen\b.*\bnautilus\b",
            r"\bopen\b.*\bfolder\b",
        ],
        "intent": "open_file_manager",
        "command": "nautilus",
        "dangerous": False,
        "description": "Opening file manager",
    },

    # --- List Files ---
    {
        "patterns": [
            r"\blist\b.*\bfiles\b",
            r"\bshow\b.*\bfiles\b",
            r"\bwhat\b.*\bfiles\b",
            r"\bdirectory\b.*\blisting\b",
        ],
        "intent": "list_files",
        "command": "ls -la",
        "dangerous": False,
        "description": "Listing files in current directory",
    },

    # --- Disk Space ---
    {
        "patterns": [
            r"\bdisk\b.*\bspace\b",
            r"\bstorage\b.*\busage\b",
            r"\bcheck\b.*\bdisk\b",
            r"\bhow\s+much\s+space\b",
            r"\bfree\b.*\bspace\b",
        ],
        "intent": "disk_space",
        "command": "df -h",
        "dangerous": False,
        "description": "Checking disk space",
    },

    # --- Memory ---
    {
        "patterns": [
            r"\bmemory\b.*\busage\b",
            r"\bcheck\b.*\bmemory\b",
            r"\bram\b.*\busage\b",
            r"\bhow\s+much\s+memory\b",
            r"\bfree\b.*\bmemory\b",
        ],
        "intent": "memory_usage",
        "command": "free -h",
        "dangerous": False,
        "description": "Checking memory usage",
    },

    # --- Screenshot ---
    {
        "patterns": [
            r"\btake\b.*\bscreenshot\b",
            r"\bscreenshot\b",
            r"\bcapture\b.*\bscreen\b",
            r"\bscreen\s*shot\b",
        ],
        "intent": "screenshot",
        "command": "gnome-screenshot",
        "dangerous": False,
        "description": "Taking a screenshot",
    },

    # --- Date / Time ---
    {
        "patterns": [
            r"\bwhat\s+time\b",
            r"\bcurrent\s+time\b",
            r"\bwhat\b.*\bdate\b",
            r"\btoday.?s\s+date\b",
            r"\btell\b.*\btime\b",
        ],
        "intent": "get_time",
        "command": "__builtin_time__",
        "dangerous": False,
        "description": "Getting current date and time",
    },

    # --- Play Music ---
    {
        "patterns": [
            r"\bplay\b.*\bmusic\b",
            r"\bplay\b.*\bsong\b",
            r"\bplay\b.*\baudio\b",
            r"\bstart\b.*\bmusic\b",
        ],
        "intent": "play_music",
        "command": "xdg-open /usr/share/sounds/",
        "dangerous": False,
        "description": "Opening music player",
    },

    # --- System Info ---
    {
        "patterns": [
            r"\bsystem\b.*\binfo\b",
            r"\bsystem\b.*\bdetails\b",
            r"\babout\b.*\bsystem\b",
            r"\bos\b.*\binfo\b",
        ],
        "intent": "system_info",
        "command": "uname -a",
        "dangerous": False,
        "description": "Getting system information",
    },

    # --- Network / IP ---
    {
        "patterns": [
            r"\bip\s*address\b",
            r"\bmy\b.*\bip\b",
            r"\bnetwork\b.*\binfo\b",
            r"\bcheck\b.*\bnetwork\b",
        ],
        "intent": "network_info",
        "command": "hostname -I",
        "dangerous": False,
        "description": "Checking network information",
    },

    # --- Uptime ---
    {
        "patterns": [
            r"\buptime\b",
            r"\bhow\s+long\b.*\brunning\b",
            r"\bsystem\b.*\buptime\b",
        ],
        "intent": "uptime",
        "command": "uptime",
        "dangerous": False,
        "description": "Checking system uptime",
    },

    # ===================== DANGEROUS COMMANDS =====================

    # --- Shutdown ---
    {
        "patterns": [
            r"\bshut\s*down\b",
            r"\bpower\s*off\b",
            r"\bturn\s*off\b.*\bcomputer\b",
            r"\bturn\s*off\b.*\bsystem\b",
        ],
        "intent": "shutdown",
        "command": "shutdown now",
        "dangerous": True,
        "description": "⚠️ Shutting down the system",
    },

    # --- Reboot ---
    {
        "patterns": [
            r"\breboot\b",
            r"\brestart\b.*\bsystem\b",
            r"\brestart\b.*\bcomputer\b",
        ],
        "intent": "reboot",
        "command": "reboot",
        "dangerous": True,
        "description": "⚠️ Rebooting the system",
    },

    # --- Delete Files ---
    {
        "patterns": [
            r"\bdelete\b.*\bfiles?\b",
            r"\bremove\b.*\bfiles?\b",
            r"\berase\b.*\bfiles?\b",
        ],
        "intent": "delete_files",
        "command": None,  # Never auto-execute
        "dangerous": True,
        "description": "⚠️ File deletion requested (blocked for safety)",
    },

    # --- System Update ---
    {
        "patterns": [
            r"\bsystem\b.*\bupdate\b",
            r"\bupdate\b.*\bsystem\b",
            r"\bapt\b.*\bupdate\b",
        ],
        "intent": "system_update",
        "command": "sudo apt update && sudo apt upgrade -y",
        "dangerous": True,
        "description": "⚠️ Running system update",
    },
]


# ---------------------------------------------------------------------------
# Pending confirmations store (in-memory, keyed by token)
# ---------------------------------------------------------------------------
_pending_confirmations = {}


def detect_command(text: str) -> dict | None:
    """
    Scan transcribed text against known command patterns.

    Returns:
        dict with intent, command, dangerous, description — or None
        if no command is recognised.
    """
    cleaned = text.strip().lower()

    for entry in COMMAND_REGISTRY:
        for pattern in entry["patterns"]:
            if re.search(pattern, cleaned):
                return {
                    "intent": entry["intent"],
                    "action": entry["command"],
                    "dangerous": entry["dangerous"],
                    "description": entry["description"],
                }

    return None


def execute_command(cmd_info: dict, confirmed: bool = False) -> dict:
    """
    Execute a detected command.

    For dangerous commands:
      - If not confirmed → return a confirmation token.
      - If confirmed     → execute the command.

    Returns a result dict suitable for the API response.
    """
    intent = cmd_info.get("intent", "")
    action = cmd_info.get("action")
    dangerous = cmd_info.get("dangerous", False)

    # ---- Handle dangerous commands ----
    if dangerous and not confirmed:
        token = str(uuid.uuid4())
        _pending_confirmations[token] = cmd_info
        return {
            "intent": intent,
            "action": action,
            "executed": False,
            "requires_confirmation": True,
            "confirmation_token": token,
            "warning": (
                f"{cmd_info['description']}. "
                "This is a potentially dangerous operation. "
                "Please confirm to proceed."
            ),
            "output": "",
        }

    # ---- Built-in (Python) commands ----
    if action == "__builtin_time__":
        now = datetime.now().strftime("%A, %B %d, %Y — %I:%M %p")
        return {
            "intent": intent,
            "action": "datetime (built-in)",
            "executed": True,
            "requires_confirmation": False,
            "output": f"Current date and time: {now}",
        }

    # ---- Blocked commands (no action defined) ----
    if action is None:
        return {
            "intent": intent,
            "action": None,
            "executed": False,
            "requires_confirmation": False,
            "output": "This command has been blocked for safety.",
        }

    # ---- Execute Linux command via subprocess ----
    try:
        result = subprocess.run(
            action,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            output = result.stderr.strip() if not output else output

        return {
            "intent": intent,
            "action": action,
            "executed": True,
            "requires_confirmation": False,
            "output": output or "Command executed successfully.",
        }
    except subprocess.TimeoutExpired:
        return {
            "intent": intent,
            "action": action,
            "executed": False,
            "requires_confirmation": False,
            "output": "Command timed out after 15 seconds.",
        }
    except Exception as e:
        return {
            "intent": intent,
            "action": action,
            "executed": False,
            "requires_confirmation": False,
            "output": f"Execution error: {str(e)}",
        }


def confirm_and_execute(token: str) -> dict:
    """
    Execute a previously-pending dangerous command after confirmation.
    """
    cmd_info = _pending_confirmations.pop(token, None)
    if cmd_info is None:
        return {
            "intent": None,
            "action": None,
            "executed": False,
            "requires_confirmation": False,
            "output": "Invalid or expired confirmation token.",
        }

    return execute_command(cmd_info, confirmed=True)
