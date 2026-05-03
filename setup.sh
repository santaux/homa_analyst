#!/bin/bash
# Homa Energy Analyst — one-time setup (macOS / Linux)
set -e

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Installing MCP server dependencies..."
.venv/bin/pip install -r mcp/requirements.txt -q

echo ""
echo "Setup complete."
echo ""
echo "Next step:"
echo "  cd $(pwd)"
echo "  claude"
echo ""
echo "Claude Code will connect to the MCP server automatically via .mcp.json"
