# Antigravity EMS / Timesheet Generator

A customizable skill and plugin for Google Antigravity that transforms your daily agent conversations and development activity into clean, compliant timesheet / EMS task entries.

---

## Key Features

1. **First-Time Interactive Onboarding**:
   - Asks the user to provide 1-2 sample entries matching their preferred style or choose from built-in presets (Tab-separated EMS, Ticket Bullets, Markdown Table).
   - Configures custom formatting constraints (e.g., character limits, non-technical summaries, required fields).
   - Inquires if the user wants an automated end-of-day summary generated automatically.

2. **Automated Context Parsing**:
   - Analyzes conversation transcripts to extract ticket numbers, root cause summaries, investigated files, and solutions.
   - Enforces strict character limits (e.g. `< 700 characters`) and consistent formatting.

3. **End-of-Day Scheduled Automation**:
   - Integrates with Antigravity's scheduled sidecars to summarize tasks at your chosen end-of-day time (e.g., 6:30 PM local time).

---

## Repository Structure

```text
antigravity-ems/
├── plugin.json                           # Antigravity plugin manifest
├── config/
│   └── default-config.json               # Default formatting templates and presets
├── skills/
│   └── ems/
│       ├── SKILL.md                      # Skill definition and execution workflow
│       └── scripts/
│           ├── setup_wizard.py           # Onboarding & configuration manager
│           └── extract_context.py        # Transcript & ticket parser
└── sidecars/
    └── daily-ems-summary/
        └── sidecar.json.template         # Scheduled automation template
```

---

## Installation

### Method 1: Global Plugin (Recommended)

Clone this repository directly into your Antigravity global plugins directory:

```bash
git clone https://github.com/<your-username>/antigravity-ems.git ~/.gemini/config/plugins/ems
```

### Method 2: Project-Scoped Customization

Clone into your repository's `.agents` directory:

```bash
git clone https://github.com/<your-username>/antigravity-ems.git <your-project-root>/.agents/plugins/ems
```

---

## Usage

* **First Run**: Type `/ems` in chat. The agent will detect that you haven't set up your preferences yet and will ask you for your sample entries, constraints, and daily automation preference.
* **Daily Generation**:
  - `/ems` or `/ems today`: Generates entries for today's active tasks.
  - `/ems <conversation-id>`: Generates an entry for a specific conversation.
  - `/ems yesterday`: Generates entries for yesterday's tasks.
* **Reconfigure**:
  - `/ems setup`: Re-runs the onboarding interview to update your preferred format, samples, or schedule.
