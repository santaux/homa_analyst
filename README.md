# Homa Energy — Analyst Setup

Conversational data analysis of the Homa Energy platform database using Claude Code + a local MCP server.

---

## Prerequisites

- **Python 3.10 or newer** — check with `python3 --version`
- **Claude Code** — install from [claude.ai/code](https://claude.ai/code)

---

## Setup (one time)

### macOS / Linux

```bash
# From the homa-analyst/ directory:
chmod +x setup.sh
./setup.sh
```

### Windows

```bat
setup.bat
```

The setup script creates a `.venv/` virtual environment, installs the `mcp` package, and on Windows also rewrites `.mcp.json` with the correct Windows paths.

---

### Verify the database is present

```
homa-analyst/
├── homa_db.sqlite3   ← must be here
├── CLAUDE.md
├── .mcp.json
├── setup.sh / setup.bat
└── mcp/
    ├── server.py
    └── requirements.txt
```

If `homa_db.sqlite3` is missing, place it in this folder before proceeding.

### Open the project in Claude Code

```bash
cd homa-analyst
claude
```

Claude Code will automatically detect `.mcp.json` and connect to the MCP server on startup.  
You should see `homa-energy` listed under active MCP servers in the Claude Code status bar.

---

## How it works

```
You (natural language question)
        ↓
  Claude Code (CLAUDE.md sets context)
        ↓
  MCP server (server.py)
        ↓
  homa_db.sqlite3 (read-only)
        ↓
  Answer in plain language
```

The MCP server exposes four tools:

| Tool | Description |
|------|-------------|
| `list_tables` | All tables with business descriptions |
| `describe_table` | Columns + descriptions for a specific table |
| `get_schema` | Full schema overview in one call |
| `execute_query` | Run a SELECT query (max 500 rows returned) |

Only `SELECT` and `WITH …` queries are permitted. Any attempt to modify data is blocked.

---

## Example session

```
> Which countries have the highest average daily energy consumption?

> How has total CO₂ output trended from January to April 2026?

> Do Premium users open the app more frequently than free-tier users?

> Which support topics have the lowest customer satisfaction scores?

> Compare projected vs actual daily consumption — how accurate are our forecasts?
```

---

## Database tables

| Table | Rows (approx.) | Description |
|-------|---------------|-------------|
| `users` | 50 | App users |
| `homes` | 50 | Monitored premises |
| `devices` | 50 | Smart meter hardware |
| `energy_prices` | ~20 | Reference tariffs by country |
| `energy_readings` | ~115,000 | Hourly consumption (core fact table) |
| `daily_stats` | ~6,000 | Pre-aggregated daily totals |
| `weekly_stats` | ~700 | Pre-aggregated weekly totals |
| `monthly_stats` | ~200 | Pre-aggregated monthly totals |
| `projections` | ~6,000 | End-of-day forecasts |
| `user_sessions` | ~18,000 | App usage sessions |
| `support_conversations` | ~60 | Support tickets |
| `support_messages` | ~350 | Messages within tickets |

Data covers **January 1 – April 30, 2026**.

---

## Troubleshooting

**`Database not found` error**  
→ Make sure `homa_db.sqlite3` is in the `homa-analyst/` folder (same level as `CLAUDE.md`).

**`ModuleNotFoundError: mcp`**  
→ Run `pip install -r mcp/requirements.txt` and restart Claude Code.

**MCP server not connecting on Windows**  
→ Change `"command": "python3"` to `"command": "python"` in `.mcp.json`.

**Claude says it cannot run queries**  
→ Confirm the MCP server is listed as active (green) in Claude Code. If not, restart Claude Code from the `homa-analyst/` directory.
