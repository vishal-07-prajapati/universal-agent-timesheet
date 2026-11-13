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
    # Supports user profile or custom AGY brain directory
    user_home = os.path.expanduser('~')
    default_brain = os.path.join(user_home, '.gemini', 'antigravity', 'brain')
    if os.path.exists(default_brain):
        return default_brain
    return default_brain

def find_convs_by_date(target_date=None):
    brain = get_brain_dir()
    if not os.path.exists(brain):
        return []
    
    if target_date is None:
        target_date = datetime.date.today()

    active_convs = []
    for item in os.listdir(brain):
        p = os.path.join(brain, item)
        if os.path.isdir(p) and len(item) == 36:
            try:
                mtime = datetime.date.fromtimestamp(os.path.getmtime(p))
                if mtime == target_date:
                    active_convs.append(item)
            except Exception:
                continue
    return active_convs

def parse_conversation(conv_id):
    brain = get_brain_dir()
    log_path = os.path.join(brain, conv_id, '.system_generated', 'logs', 'transcript.jsonl')
    if not os.path.exists(log_path):
        return None

    user_requests = []
    model_summaries = []
    tickets = set()
    code_files = set()

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            try:
                data = json.loads(line)
            except Exception:
                continue

            content = data.get('content') or ''
            step_type = data.get('type')

            if step_type == 'USER_INPUT' and content:
                clean = re.sub(r'<USER_REQUEST>\s*', '', content)
                clean = re.sub(r'</USER_REQUEST>.*', '', clean, flags=re.DOTALL)
                clean = clean.strip()
                if clean and len(clean) > 3 and not re.match(r'^[0-9a-fA-F-]{36}$', clean):
                    user_requests.append(clean)
                    # Ticket numbers (e.g., 13406610686, 13519602243, 88574, 10466)
                    found_tickets = re.findall(r'\b(?:CE21#)?(\d{5,12})\b', clean)
                    for t in found_tickets:
                        tickets.add(t)

            elif step_type == 'PLANNER_RESPONSE' and content:
                lower = content.lower()
                if any(k in lower for k in ['root cause', 'investigation findings', 'solution', 'summary', 'completed', 'deliverables', 'actions taken']):
                    model_summaries.append(content[:800])

            # Check tool calls for modified or inspected files
            tool_calls = data.get('tool_calls') or []
            for tc in tool_calls:
                args = tc.get('args') or {}
                cmd = str(args.get('CommandLine') or '') + ' ' + str(args.get('Path') or '')
                for ext in ['.cs', '.cshtml', '.sql', '.js', '.ts', '.py']:
                    matches = re.findall(rf'[\w\.-]+{re.escape(ext)}', cmd)
                    for m in matches:
                        if not m.startswith('transcript') and not m.startswith('output'):
                            code_files.add(m)

    return {
        'conv_id': conv_id,
        'tickets': list(tickets),
        'files_touched': list(code_files)[:10],
        'user_requests': user_requests[:4],
        'model_summaries': model_summaries[-3:] if model_summaries else []
    }

def print_summary(info):
    if not info:
        print("Transcript not found.")
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
        print(f"Found {len(convs)} conversation(s) for {date}:")
        for c in convs:
            print_summary(parse_conversation(c))
    else:
        for a in args:
            if re.match(r'^[0-9a-fA-F-]{36}$', a):
                print_summary(parse_conversation(a))
            else:
                print(f"Skipping non-UUID argument: {a}")
