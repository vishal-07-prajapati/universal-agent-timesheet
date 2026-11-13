import sys
import os
import json
import re
import datetime

# Ensure utf-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CONFIG_DIR = os.path.expanduser(r'~/.gemini/config')
LEDGER_PATH = os.path.join(CONFIG_DIR, 'ems_daily_ledger.json')

def get_brain_dir():
    user_home = os.path.expanduser('~')
    return os.path.join(user_home, '.gemini', 'antigravity', 'brain')

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def find_convs_by_date(target_date=None):
    if target_date is None:
        target_date = datetime.date.today()

    target_date_str = target_date.strftime('%Y-%m-%d')
    
    # 1. FAST PATH: Check the real-time daily ledger first!
    ledger = load_ledger()
    if target_date_str in ledger and ledger[target_date_str]:
        conv_ids = list(ledger[target_date_str].keys())
        # Filter out current active timesheet generator session if present
        conv_ids = [c for c in conv_ids if len(c) == 36]
        if conv_ids:
            return conv_ids

    # 2. FALLBACK PATH: Directory scan if ledger is empty/not present
    brain = get_brain_dir()
    if not os.path.exists(brain):
        return []

    active_convs = []
    for item in os.listdir(brain):
        p = os.path.join(brain, item)
        if not (os.path.isdir(p) and len(item) == 36):
            continue

        log_path = os.path.join(p, '.system_generated', 'logs', 'transcript.jsonl')
        if not os.path.exists(log_path):
            continue

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
            active_convs.append(item)

    return active_convs

def parse_conversation(conv_id, target_date=None):
    brain = get_brain_dir()
    log_path = os.path.join(brain, conv_id, '.system_generated', 'logs', 'transcript.jsonl')
    
    # Check ledger first for cached metadata
    target_date_str = target_date.strftime('%Y-%m-%d') if target_date else None
    cached_info = None
    if target_date_str:
        ledger = load_ledger()
        if target_date_str in ledger and conv_id in ledger[target_date_str]:
            cached_info = ledger[target_date_str][conv_id]
            if not os.path.exists(log_path) and cached_info.get("transcript_path"):
                log_path = cached_info["transcript_path"]

    if not os.path.exists(log_path):
        return None

    user_requests = []
    model_summaries = []
    tickets = set()
    code_files = set()
    is_timesheet_generator = False

    if cached_info and cached_info.get("tickets"):
        for t in cached_info["tickets"]:
            tickets.add(t)

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                data = json.loads(line)
            except Exception:
                continue

            created_at = str(data.get('created_at') or '')
            if target_date_str and target_date_str not in created_at:
                continue

            content = data.get('content') or ''
            step_type = data.get('type')

            if step_type == 'USER_INPUT' and content:
                if 'Task Entry / Timesheet Generator' in content or '/ems' in content:
                    is_timesheet_generator = True

                clean = re.sub(r'<USER_REQUEST>\s*', '', content)
                clean = re.sub(r'</USER_REQUEST>.*', '', clean, flags=re.DOTALL)
                clean = clean.strip()
                if clean and len(clean) > 3 and not re.match(r'^[0-9a-fA-F-]{36}$', clean):
                    user_requests.append(clean)
                    found_tickets = re.findall(r'\b(?:CE21#)?(\d{5,12})\b', clean)
                    for t in found_tickets:
                        tickets.add(t)

            elif step_type == 'PLANNER_RESPONSE' and content:
                lower = content.lower()
                if any(k in lower for k in ['root cause', 'investigation findings', 'solution', 'summary', 'completed', 'deliverables', 'actions taken', 'fix summary']):
                    model_summaries.append(content[:800])

            tool_calls = data.get('tool_calls') or []
            for tc in tool_calls:
                args = tc.get('args') or {}
                cmd = str(args.get('CommandLine') or '') + ' ' + str(args.get('Path') or '')
                for ext in ['.cs', '.cshtml', '.sql', '.js', '.ts', '.py']:
                    matches = re.findall(rf'[\w\.-]+{re.escape(ext)}', cmd)
                    for m in matches:
                        if not m.startswith('transcript') and not m.startswith('output'):
                            code_files.add(m)

    if is_timesheet_generator and not tickets:
        return None

    if not user_requests and not model_summaries and not cached_info:
        return None

    if not user_requests and cached_info and cached_info.get("user_requests"):
        user_requests = cached_info["user_requests"]

    return {
        'conv_id': conv_id,
        'tickets': list(tickets),
        'files_touched': list(code_files)[:10],
        'user_requests': user_requests[-4:],
        'model_summaries': model_summaries[-3:] if model_summaries else []
    }

def print_summary(info):
    if not info:
        return

    print(f"=== CONVERSATION: {info['conv_id']} ===")
    if info['tickets']:
        print(f"Tickets Detected: {', '.join(info['tickets'])}")
    if info['files_touched']:
        print(f"Key Files: {', '.join(info['files_touched'])}")
    print("User Requests Summary:")
    for r in info['user_requests']:
        snippet = r.replace('\r\n', ' ').replace('\n', ' ')[:200]
        print(f"  * {snippet}")
    print("Investigation / Fix Highlights:")
    for s in info['model_summaries']:
        snippet = s.replace('\r\n', ' ').replace('\n', ' ')[:250]
        print(f"  - {snippet}")
    print()

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0].lower() in ['today', 'yesterday']:
        date = datetime.date.today()
        if args and args[0].lower() == 'yesterday':
            date -= datetime.timedelta(days=1)
        convs = find_convs_by_date(date)
        print(f"Found {len(convs)} active/reused conversation(s) for {date}:")
        for c in convs:
            info = parse_conversation(c, target_date=date)
            if info:
                print_summary(info)
    else:
        for a in args:
            if re.match(r'^[0-9a-fA-F-]{36}$', a):
                print_summary(parse_conversation(a))
            else:
                print(f"Skipping non-UUID argument: {a}")
