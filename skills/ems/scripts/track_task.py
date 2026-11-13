#!/usr/bin/env python3
"""
Silent EMS Task Tracker (Hook Script)
Silently tracks active and reused tasks/conversations as they happen, maintaining a daily ledger.
Zero overhead (<15ms), safe and non-blocking.
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
LEDGER_PATH = os.path.join(CONFIG_DIR, 'ems_daily_ledger.json')

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_ledger(ledger):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        # Keep only the last 30 days of history to keep file tiny
        dates = sorted(ledger.keys())
        if len(dates) > 30:
            for d in dates[:-30]:
                del ledger[d]
        with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
            json.dump(ledger, f, indent=2)
    except Exception:
        pass

def track_event(payload):
    conv_id = payload.get('conversationId')
    if not conv_id or len(conv_id) != 36:
        return

    user_input = payload.get('lastUserInput') or ''
    
    # Ignore purely timesheet generator commands
    if user_input.strip().startswith('/ems') or 'Task Entry / Timesheet Generator' in user_input:
        return
    # Ignore if user input is just 1 or more UUIDs
    clean_lines = [l.strip() for l in user_input.split('\n') if l.strip()]
    if clean_lines and all(re.match(r'^[0-9a-fA-F-]{36}$', l) for l in clean_lines):
        return

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    now_iso = datetime.datetime.now().isoformat()

    ledger = load_ledger()
    if today_str not in ledger:
        ledger[today_str] = {}

    day_data = ledger[today_str]
    
    # Extract ticket IDs
    tickets = re.findall(r'\b(?:CE21#)?(\d{5,12})\b', user_input)
    
    clean_snippet = re.sub(r'<[^>]+>', '', user_input).strip()
    clean_snippet = clean_snippet.replace('\r\n', ' ').replace('\n', ' ')[:200]

    if conv_id not in day_data:
        day_data[conv_id] = {
            "first_seen": now_iso,
            "last_activity": now_iso,
            "tickets": tickets,
            "user_requests": [clean_snippet] if clean_snippet else [],
            "transcript_path": payload.get('transcriptPath') or ''
        }
    else:
        entry = day_data[conv_id]
        entry["last_activity"] = now_iso
        for t in tickets:
            if t not in entry["tickets"]:
                entry["tickets"].append(t)
        if clean_snippet and clean_snippet not in entry["user_requests"]:
            if len(entry["user_requests"]) >= 5:
                entry["user_requests"].pop(0)
            entry["user_requests"].append(clean_snippet)
        if not entry.get("transcript_path") and payload.get('transcriptPath'):
            entry["transcript_path"] = payload.get('transcriptPath')

    save_ledger(ledger)

def main():
    try:
        # Read hook payload from stdin
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
                track_event(data)
    except Exception:
        pass

    # Hooks must return a JSON response
    sys.stdout.write(json.dumps({}) + "\n")
    sys.stdout.flush()

if __name__ == '__main__':
    main()
