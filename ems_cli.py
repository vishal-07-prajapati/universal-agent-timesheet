#!/usr/bin/env python3
"""
Universal Agent Timesheet & EMS CLI
Use standalone in terminal or invoke from any AI agent (Claude Code, Cursor, Windsurf, Antigravity, etc.)
"""

import sys
import os
import json
import re
import datetime

# Ensure utf-8 stdio
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CONFIG_DIR = os.path.expanduser(r'~/.gemini/config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'ems-user-config.json')

DEFAULT_SAMPLE = """CE21\t\tDevelopment\t13519602243: Invoices Duplicated on Statements
- Investigated issue where invoices were duplicated on statements generated from Invoicing.
- Traced root cause to multi-membership accounts passing duplicate customer IDs in bulk requests.
- Analyzed stored procedures to locate redundant table joins caused by un-deduplicated parameters.
- Formulated database stored procedure fix using distinct ID evaluation to prevent duplicates.
- Drafted a clear non-technical explanation for client support detailing row selection.\t04:00\t04:00\t\tCompleted\tPending"""

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "configured": True,
        "style": "tab-separated",
        "sample": DEFAULT_SAMPLE,
        "max_characters": 700,
        "default_client": "CE21",
        "default_hours": "04:00",
        "automation": {
            "enabled": True,
            "time": "18:30",
            "timezone": "Asia/Kolkata"
        }
    }

def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    print(f"✓ Configuration saved to {CONFIG_PATH}")

def run_interactive_setup():
    print("=" * 60)
    print("  Universal Timesheet / EMS Generator - Setup Wizard")
    print("=" * 60)
    print("\nThis wizard configures your timesheet formatting preferences across all AI agents.\n")

    cfg = load_config()

    print("Step 1: Choose your preferred timesheet format:")
    print("  [1] Tab-Separated Timesheet (EMS / ERP Format) [Recommended]")
    print("  [2] Bullet-Point List with Ticket & Summary (Jira / ClickUp format)")
    print("  [3] Markdown Table (| Client | Ticket | Summary | Hours | Status |)")
    print("  [4] Custom Format (Provide your own sample)")
    
    choice = input("\nEnter choice [1-4] (default: 1): ").strip()
    if choice == "2":
        cfg["style"] = "bullet-list"
    elif choice == "3":
        cfg["style"] = "markdown-table"
    elif choice == "4":
        cfg["style"] = "custom"
        print("\nPlease paste 1-2 sample entries matching your exact format (enter an empty line when done):")
        sample_lines = []
        while True:
            line = input()
            if not line:
                break
            sample_lines.append(line)
        if sample_lines:
            cfg["sample"] = "\n".join(sample_lines)
    else:
        cfg["style"] = "tab-separated"

    print("\nStep 2: Character Limit per Entry:")
    limit_str = input("Enter max character limit (default: 700, enter 0 for none): ").strip()
    try:
        limit = int(limit_str)
        cfg["max_characters"] = limit if limit > 0 else 99999
    except Exception:
        cfg["max_characters"] = 700

    client_str = input("Default client/project name (default: CE21): ").strip()
    if client_str:
        cfg["default_client"] = client_str

    print("\nStep 3: End-of-Day Daily Automation:")
    auto_choice = input("Do you want to set up an automated daily summary at the end of each workday? [Y/n]: ").strip().lower()
    if auto_choice != 'n':
        auto_time = input("What time should it run? (default: 18:30 / 6:30 PM): ").strip() or "18:30"
        auto_tz = input("Your timezone? (default: Asia/Kolkata): ").strip() or "Asia/Kolkata"
        cfg["automation"] = {
            "enabled": True,
            "time": auto_time,
            "timezone": auto_tz,
            "cron": f"CRON_TZ={auto_tz} {auto_time.split(':')[1]} {auto_time.split(':')[0]} * * *"
        }
    else:
        cfg["automation"]["enabled"] = False

    cfg["configured"] = True
    save_config(cfg)
    print("\n✓ Setup complete! You can now use `/ems` in Antigravity/Claude or run `python ems_cli.py --today` anywhere.")

def get_brain_dir():
    user_home = os.path.expanduser('~')
    return os.path.join(user_home, '.gemini', 'antigravity', 'brain')

def extract_tasks_for_date(target_date):
    brain = get_brain_dir()
    target_date_str = target_date.strftime('%Y-%m-%d')
    tasks = []
    
    if not os.path.exists(brain):
        return tasks

    for item in os.listdir(brain):
        p = os.path.join(brain, item)
        if not (os.path.isdir(p) and len(item) == 36):
            continue

        log_path = os.path.join(p, '.system_generated', 'logs', 'transcript.jsonl')
        if not os.path.exists(log_path):
            continue

        # Check modification time or scan recent steps for target_date
        is_active = False
        try:
            mtime = datetime.date.fromtimestamp(os.path.getmtime(log_path))
            if mtime == target_date:
                is_active = True
        except Exception:
            pass

        if not is_active:
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(max(0, os.path.getsize(log_path) - 51200))
                    if target_date_str in f.read():
                        is_active = True
            except Exception:
                pass

        if is_active:
            task = parse_transcript_file(item, log_path, target_date_str)
            if task:
                tasks.append(task)

    return tasks

def parse_transcript_file(conv_id, log_path, target_date_str=None):
    tickets = set()
    requests = []
    summaries = []
    is_timesheet_generator = False

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue

            created_at = str(d.get('created_at') or '')
            if target_date_str and target_date_str not in created_at:
                continue

            c = d.get('content') or ''
            t = d.get('type')

            if t == 'USER_INPUT' and c:
                if 'Task Entry / Timesheet Generator' in c or '/ems' in c:
                    is_timesheet_generator = True
                clean = re.sub(r'<[^>]+>', '', c).strip()
                if len(clean) > 5 and not re.match(r'^[0-9a-fA-F-]{36}$', clean):
                    requests.append(clean[:200])
                    for m in re.findall(r'\b(?:CE21#)?(\d{5,12})\b', clean):
                        tickets.add(m)
            elif t == 'PLANNER_RESPONSE' and c:
                if any(k in c.lower() for k in ['root cause', 'findings', 'completed', 'deliverables', 'solution', 'fix summary']):
                    summaries.append(c[:400])

    if is_timesheet_generator and not tickets:
        return None

    if not requests and not summaries:
        return None

    return {
        'id': conv_id,
        'tickets': list(tickets),
        'requests': requests[-3:],
        'summaries': summaries[-2:] if summaries else []
    }

def main():
    args = sys.argv[1:]
    cfg = load_config()

    if not args or '--help' in args or '-h' in args:
        print("Usage:")
        print("  python ems_cli.py --setup             Run interactive setup wizard")
        print("  python ems_cli.py --today             Generate timesheet for today's tasks")
        print("  python ems_cli.py --yesterday         Generate timesheet for yesterday's tasks")
        print("  python ems_cli.py <conversation-id>   Generate timesheet for a specific conversation")
        return

    if '--setup' in args:
        run_interactive_setup()
        return

    target_date = datetime.date.today()
    if '--yesterday' in args:
        target_date -= datetime.timedelta(days=1)

    print(f"\nAnalyzing activity for {target_date} (including modified & reused conversations)...")
    tasks = extract_tasks_for_date(target_date)
    
    if not tasks:
        print("No Antigravity activity found for this date. Checking git activity...")
        import subprocess
        try:
            res = subprocess.run(['git', 'log', '--since="midnight"', '--oneline'], capture_output=True, text=True)
            if res.stdout.strip():
                print("Recent git commits:")
                for line in res.stdout.strip().split('\n')[:5]:
                    print("  * " + line)
        except Exception:
            pass
        return

    print(f"Found {len(tasks)} active/reused task session(s). Formatted entries matching your configuration:\n")
    print("=" * 60)
    for t in tasks:
        ticket = t['tickets'][0] if t['tickets'] else "Task Investigation & Fix"
        client = cfg.get("default_client", "CE21")
        hours = cfg.get("default_hours", "04:00")
        
        header = f"{client}\t\tDevelopment\t{ticket}: Task Implementation & Investigation"
        bullets = []
        for r in t['requests'][:2]:
            clean_r = r.replace('\r\n', ' ').replace('\n', ' ')[:100]
            bullets.append(f"- Investigated: {clean_r}")
        for s in t['summaries'][:2]:
            clean_s = s.replace('\r\n', ' ').replace('\n', ' ')[:100]
            bullets.append(f"- Resolved: {clean_s}")

        if not bullets:
            bullets.append("- Completed development, root cause analysis, and code verification.")

        last_bullet = bullets[-1] + f"\t{hours}\t{hours}\t\tCompleted\tPending"
        bullets[-1] = last_bullet

        entry = header + "\n" + "\n".join(bullets)
        print(f"\n```markdown\n{entry}\n```")
        print(f"Length: {len(entry)} characters (limit: {cfg.get('max_characters', 700)})")

if __name__ == '__main__':
    main()
