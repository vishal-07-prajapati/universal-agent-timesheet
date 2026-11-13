# Universal Agent Timesheet & EMS Generator

A universal, agent-agnostic tool, MCP server, and skill that automatically converts daily AI coding sessions, conversation history, and git activity into clean, compliant daily EMS / timesheet entries.

Designed to work across **any AI agent**:
- **Google Antigravity** (Skills, Plugins, Scheduled Automations)
- **Claude Code** (Slash Commands, Plugins, MCP)
- **Cursor & Windsurf** (MCP Server, Agent Rules)
- **Cline & Roo Code** (MCP Server)
- **Standalone Terminal / Shell** (CLI)

---

## Key Features

1. **First-Time Interactive Setup**:
   - Asks the user to choose their preferred timesheet format or paste their own sample.
   - Enforces character constraints (e.g., strictly `< 700 characters` per entry for EMS).
   - Configures end-of-day scheduled automations.
2. **Universal MCP Server**:
   - Zero-dependency Model Context Protocol server (`mcp/server.py`) using pure Python standard libraries.
3. **Multi-Agent Integrations**:
   - Works via slash commands (`/ems`), MCP tool calls (`generate_timesheet`, `setup_preferences`), or terminal CLI (`python ems_cli.py --today`).
4. **Automated Context Parsing**:
   - Automatically extracts ticket numbers, root cause summaries, investigated files, and fixes from conversation transcripts and Git commits.

---

## Supported Agent Integrations

### 1. Google Antigravity
Clone directly into your Antigravity global plugins directory:
```bash
git clone https://github.com/vishal-07-prajapati/universal-agent-timesheet.git ~/.gemini/config/plugins/ems
```
* **Usage**: Type `/ems` or `/ems today` in any chat session.

### 2. Claude Code
Add as an MCP server:
```bash
claude mcp add universal-timesheet python /path/to/universal-agent-timesheet/mcp/server.py
```
Or copy `.claude/commands/ems.md` into your project's `.claude/commands/`.
* **Usage**: Type `/ems` in Claude Code.

### 3. Cursor & Windsurf
Add to your Cursor / Windsurf MCP configuration (`mcp_config.json`):
```json
{
  "mcpServers": {
    "universal-timesheet": {
      "command": "python",
      "args": ["/path/to/universal-agent-timesheet/mcp/server.py"]
    }
  }
}
```
* **Usage**: Ask the agent in chat: *"Generate my timesheet entry for today"* or *"Run /ems"*.

### 4. Standalone CLI (Terminal)
Works directly from any shell without needing an AI agent open:
```bash
# First-time interactive setup
python ems_cli.py --setup

# Generate entries for today's tasks
python ems_cli.py --today

# Generate entries for yesterday's tasks
python ems_cli.py --yesterday
```

---

## First-Time User Experience

On the very first run, the tool prompts the user with 3 questions:
1. **Format Sample**: Choose between Tab-Separated EMS, Ticket Bullets, Markdown Table, or paste a custom sample.
2. **Limits**: Set max character limits (default: 700) and default client/project name.
3. **Daily Automation**: Option to set up an end-of-day scheduled task (e.g. 6:30 PM local time).

Preferences are persisted to `~/.gemini/config/ems-user-config.json` and can be updated anytime with `python ems_cli.py --setup` or `/ems setup`.
