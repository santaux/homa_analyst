@echo off
REM Homa Energy Analyst — one-time setup (Windows)

echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    exit /b 1
)

echo Installing MCP server dependencies...
.venv\Scripts\pip install -r mcp\requirements.txt -q

echo.
echo Updating .mcp.json for Windows paths...
(
echo {
echo   "mcpServers": {
echo     "homa-energy": {
echo       "command": ".venv\\Scripts\\python.exe",
echo       "args": ["mcp/server.py"]
echo     }
echo   }
echo }
) > .mcp.json

echo.
echo Setup complete.
echo.
echo Next step:
echo   Open this folder in Claude Code
echo   claude .
echo.
echo Claude Code will connect to the MCP server automatically via .mcp.json
