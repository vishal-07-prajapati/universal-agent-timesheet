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

def get_brain_dir():
    user_home = os.path.expanduser('~')
    return os.path.join(user_home, '.gemini', 'antigravity', 'brain')

def find_convs_by_date(target_date=None):
    brain = get_brain_dir()
    if not os.path.exists(brain):
        return []
    
    if target_date is None:
        target_date = datetime.date.today()

    target_date_str = target_date.strftime('%Y-%m-%d')
    active_convs = []

    for item in os.listdir(brain):
        p = os.path.join(brain, item)
        if not (os.path.isdir(p) and len(item) == 36):
            continue

        log_path = os.path.join(p, '.system_generated', 'logs', 'transcript.jsonl')
        if not os.path.exists(log_path):
            continue

        # Check file modification time first (catches modified / reused conversations)
        try:
            mtime = datetime.date.fromtimestamp(os.path.getmtime(log_path))
            if mtime == target_date:
                active_convs.append(item)
                continue
        except Exception:
            pass

        # Also scan transcript tail to check if any step was created on target_date
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last 50KB to check recent steps
                f.seek(max(0, os.path.getsize(log_path) - 51200))
                tail = f.read()
                if target_date_str in tail:
                    active_convs.append(item)
        except Exception:
            pass

    return active_convs

def parse_conversation(conv_id, target_date=None):
    brain = get_brain_dir()
    log_path = os.path.join(brain, conv_id, '.system_generated', 'logs', 'transcript.jsonl')
    if not os.path.exists(log_path):
        return None

    target_date_str = target_date.strftime('%Y-%m-%d') if target_date else None

    user_requests = []
    model_summaries = []
    tickets = set()
    code_files = set()
    is_timesheet_generator = False

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                data = json.loads(line)
            except Exception:
                continue

            created_at = str(data.get('created_at') or '')
            
            # If target_date is given, strictly scope to steps created on target_date
            if target_date_str and target_date_str not in created_at:
                continue

            content = data.get('content') or ''
            step_type = data.get('type')

            if step_type == 'USER_INPUT' and content:
                # Detect if this conversation is just the timesheet generator itself
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

            # Track files touched
            tool_calls = data.get('tool_calls') or []
            for tc in tool_calls:
                args = tc.get('args') or {}
                cmd = str(args.get('CommandLine') or '') + ' ' + str(args.get('Path') or '')
                for ext in ['.cs', '.cshtml', '.sql', '.js', '.ts', '.py']:
                    matches = re.findall(rf'[\w\.-]+{re.escape(ext)}', cmd)
                    for m in matches:
                        if not m.startswith('transcript') and not m.startswith('output'):
                            code_files.add(m)

    # Filter out timesheet generator sessions from output
    if is_timesheet_generator and not tickets:
        return None

    if not user_requests and not model_summaries:
        return None

    return {
        'conv_id': conv_id,
        'tickets': list(tickets),
        'files_touched': list(code_files)[:10],
        'user_requests': user_requests[-4:],  # Most recent requests from today in this conversation
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
    print("User Requests Summary (Today's Scope):")
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
