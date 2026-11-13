#!/usr/bin/env python3
"""
Universal Agent Timesheet - Model Context Protocol (MCP) Server
Pure Python, zero external dependencies. Compatible with Antigravity, Claude Code, Cursor, Windsurf, Cline, etc.
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
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass

CONFIG_DIR = os.path.expanduser(r'~/.gemini/config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'ems-user-config.json')

DEFAULT_CONFIG = {
    "configured": False,
    "style": "tab-separated",
    "template": "[Client]\t[Module]\t[Type]\t[Task Title]\n- [Bullet 1]\n- [Bullet 2]\n- [Bullet 3]\t[Est]\t[Actual]\t\t[Status]\t[Approval]",
    "sample": "CE21\t\tDevelopment\t13519602243: Invoices Duplicated on Statements\n- Investigated issue where invoices were duplicated on statements.\n- Analyzed stored procedures to locate redundant table joins.\n- Formulated database fix using distinct evaluation.\t04:00\t04:00\t\tCompleted\tPending",
    "max_characters": 700,
    "default_client": "CE21",
    "default_hours": "04:00",
    "tone": "concise, non-technical, professional",
    "automation": {
        "enabled": False,
        "time": "18:30",
        "timezone": "Asia/Kolkata"
    }
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

def extract_from_antigravity(target_date):
    brain = os.path.join(os.path.expanduser('~'), '.gemini', 'antigravity', 'brain')
    if not os.path.exists(brain):
        return []
    
    tasks = []
    for item in os.listdir(brain):
        p = os.path.join(brain, item)
        if os.path.isdir(p) and len(item) == 36:
            try:
                mtime = datetime.date.fromtimestamp(os.path.getmtime(p))
                if mtime == target_date:
                    log_file = os.path.join(p, '.system_generated', 'logs', 'transcript.jsonl')
                    if os.path.exists(log_file):
                        tasks.append(parse_transcript(item, log_file))
            except Exception:
                continue
    return tasks

def extract_from_git():
    """Fallback: inspect git log for today's commits across active repository"""
    import subprocess
    try:
        res = subprocess.run(
            ['git', 'log', '--since="midnight"', '--pretty=format:%s|||%b', '-n', '10'],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().split('\n')
            commits = [l.strip() for l in lines if l.strip()]
            return commits
    except Exception:
        pass
    return []

def parse_transcript(conv_id, log_path):
    tickets = set()
    requests = []
    summaries = []

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            
            c = d.get('content') or ''
            t = d.get('type')

            if t == 'USER_INPUT' and c:
                clean = re.sub(r'<[^>]+>', '', c).strip()
                if len(clean) > 5 and not re.match(r'^[0-9a-fA-F-]{36}$', clean):
                    requests.append(clean[:200])
                    for m in re.findall(r'\b(?:CE21#)?(\d{5,12})\b', clean):
                        tickets.add(m)
            elif t == 'PLANNER_RESPONSE' and c:
                if any(k in c.lower() for k in ['root cause', 'findings', 'completed', 'deliverables', 'solution']):
                    summaries.append(c[:400])

    return {
        'id': conv_id,
        'tickets': list(tickets),
        'requests': requests[:3],
        'summaries': summaries[-2:] if summaries else []
    }

TOOLS = [
    {
        "name": "check_status",
        "description": "Check if user timesheet preferences and automation are configured",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "setup_preferences",
        "description": "Configure or update timesheet preferences (formatting sample, character limit, automation)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sample_entry": {"type": "string", "description": "1-2 sample entries matching user's preferred format"},
                "style": {"type": "string", "enum": ["tab-separated", "bullet-list", "markdown-table", "custom"]},
                "max_characters": {"type": "integer", "description": "Maximum character limit per entry (default 700)"},
                "default_client": {"type": "string", "description": "Default client/project name"},
                "automation_time": {"type": "string", "description": "End-of-day time for automation (e.g. 18:30)"},
                "automation_timezone": {"type": "string", "description": "IANA timezone (e.g. Asia/Kolkata)"}
            },
            "required": ["sample_entry"]
        }
    },
    {
        "name": "generate_timesheet",
        "description": "Generate timesheet entries for today, yesterday, or a specific conversation/ticket",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "'today', 'yesterday', or a conversation UUID/ticket number"},
                "hours": {"type": "string", "description": "Hours to log (default: '04:00' or based on work)"}
            }
        }
    }
]

def handle_call_tool(name, args):
    cfg = load_config()

    if name == "check_status":
        return {
            "is_configured": cfg.get("configured", False),
            "style": cfg.get("style", "tab-separated"),
            "max_characters": cfg.get("max_characters", 700),
            "automation_enabled": cfg.get("automation", {}).get("enabled", False),
            "sample": cfg.get("sample", "")
        }

    elif name == "setup_preferences":
        cfg["configured"] = True
        cfg["sample"] = args.get("sample_entry", cfg.get("sample"))
        cfg["style"] = args.get("style", "tab-separated")
        cfg["max_characters"] = args.get("max_characters", 700)
        if args.get("default_client"):
            cfg["default_client"] = args["default_client"]
        
        auto_time = args.get("automation_time")
        auto_tz = args.get("automation_timezone", "Asia/Kolkata")
        if auto_time:
            cfg["automation"] = {
                "enabled": True,
                "time": auto_time,
                "timezone": auto_tz,
                "cron": f"CRON_TZ={auto_tz} {auto_time.split(':')[1]} {auto_time.split(':')[0]} * * *"
            }
        save_config(cfg)
        return {
            "status": "success",
            "message": "Preferences saved successfully.",
            "config": cfg
        }

    elif name == "generate_timesheet":
        target = args.get("target", "today").lower()
        hours = args.get("hours", cfg.get("default_hours", "04:00"))
        
        target_date = datetime.date.today()
        if target == "yesterday":
            target_date -= datetime.timedelta(days=1)

        agy_tasks = extract_from_antigravity(target_date)
        git_tasks = extract_from_git()

        return {
            "target_date": str(target_date),
            "antigravity_tasks": agy_tasks,
            "git_activity": git_tasks,
            "format_rules": {
                "style": cfg.get("style"),
                "max_characters": cfg.get("max_characters"),
                "sample": cfg.get("sample"),
                "default_client": cfg.get("default_client", "CE21"),
                "hours": hours
            }
        }

    return {"error": f"Unknown tool {name}"}

def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line)
        except Exception:
            break

        msg_id = req.get("id")
        method = req.get("method")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "universal-agent-timesheet", "version": "1.0.0"}
                }
            }
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS}
            }
        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            out = handle_call_tool(tool_name, tool_args)
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(out, indent=2)}]
                }
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method {method} not found"}
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

if __name__ == '__main__':
    main()
