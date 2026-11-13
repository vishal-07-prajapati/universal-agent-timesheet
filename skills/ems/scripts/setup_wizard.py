import os
import sys
import json
import re

# Ensure utf-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CONFIG_DIR = os.path.expanduser(r'~/.gemini/config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'ems-user-config.json')

DEFAULT_CONFIG = {
    "configured": True,
    "style": "tab-separated",
    "template": "[Client]\t[Module]\t[Type]\t[Task Title]\n- [Bullet 1]\n- [Bullet 2]\n- [Bullet 3]\t[Est]\t[Actual]\t\t[Status]\t[Approval]",
    "sample": "CE21\t\tDevelopment\t13519602243: Invoices Duplicated on Statements\n- Investigated issue where invoices were duplicated on statements.\n- Analyzed stored procedures to locate redundant table joins.\n- Formulated database fix using distinct evaluation.\t04:00\t04:00\t\tCompleted\tPending",
    "max_characters": 700,
    "default_client": "CE21",
    "default_hours": "04:00",
    "tone": "concise, non-technical, professional",
    "bullets_count": "4-5",
    "automation": {
        "enabled": False,
        "time": "18:30",
        "timezone": "Asia/Kolkata",
        "cron": "CRON_TZ=Asia/Kolkata 30 18 * * *"
    }
}

def is_configured():
    if not os.path.exists(CONFIG_PATH):
        return False
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("configured", False)
    except Exception:
        return False

def get_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    print(f"Configuration saved to {CONFIG_PATH}")

def setup_automation(time_str="18:30", timezone="Asia/Kolkata"):
    parts = time_str.split(":")
    hour = parts[0].strip()
    minute = parts[1].strip() if len(parts) > 1 else "00"

    cron_expr = f"CRON_TZ={timezone} {int(minute)} {int(hour)} * * *"
    sidecar_dir = os.path.join(CONFIG_DIR, 'sidecars', 'daily-ems-summary')
    os.makedirs(sidecar_dir, exist_ok=True)
    sidecar_path = os.path.join(sidecar_dir, 'sidecar.json')

    skill_script = os.path.join(os.path.dirname(__file__), 'extract_context.py')

    sidecar_data = {
        "builtin": "schedule",
        "args": [
            cron_expr,
            "agentapi",
            "new-conversation",
            "--",
            f"Run python \"{skill_script}\" today to inspect today's Antigravity tasks and conversations, then generate the daily EMS timesheet entries following the ems skill in tab-separated format under 700 characters per entry."
        ],
        "restart_policy": "always",
        "display_name": "Daily EMS Summary",
        "description": f"Every day at {time_str} ({timezone}), inspects today's Antigravity tasks and generates daily EMS timesheet entries.",
        "agent_permissions": {
            "access_grants": [
                f"command(python \"{skill_script}\" today)",
                "command(python)",
                "read_file(C:\\Users\\vishal.prajapati\\.gemini\\antigravity\\brain)"
            ]
        }
    }

    with open(sidecar_path, 'w', encoding='utf-8') as f:
        json.dump(sidecar_data, f, indent=2)
    print(f"Automation schedule saved to {sidecar_path} ({cron_expr})")
    return sidecar_path

if __name__ == '__main__':
    args = sys.argv[1:]
    if '--check' in args:
        print("CONFIGURED" if is_configured() else "NOT_CONFIGURED")
    elif '--show' in args:
        print(json.dumps(get_config(), indent=2))
    elif '--init-default' in args:
        save_config(DEFAULT_CONFIG)
    else:
        print("EMS Setup Wizard Utility")
        print("Usage: python setup_wizard.py [--check | --show | --init-default]")
