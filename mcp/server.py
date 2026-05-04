"""
Homa Energy — MCP Analyst Server
Read-only SQLite access with embedded business schema context.
"""

import os
import re
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).parent.parent / "homa_db.sqlite3"

mcp = FastMCP(
    "Homa Energy Analyst",
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8001")),
)

# ── Business schema metadata ─────────────────────────────────────────────────

TABLE_DESCRIPTIONS = {
    "users": (
        "Registered app users (homeowners and tenants). Each user owns one or more homes "
        "monitored by the Homa tracker. Contains demographic, subscription and activity data."
    ),
    "homes": (
        "Physical premises where energy monitoring is active. Each home belongs to a user "
        "and has one or more devices. Contains property characteristics used for consumption modelling."
    ),
    "devices": (
        "Smart meter / P1-port energy tracker hardware installed at a home. "
        "Records model, firmware version, configured tariff and current operational status."
    ),
    "energy_prices": (
        "Reference table of live energy tariffs by country and provider. "
        "Use this to compare a device's configured tariff against the market rate for its country."
    ),
    "energy_readings": (
        "Core fact table. One row per device per hour containing kWh consumed, "
        "average watts, CO\u2082 emitted and euro cost for that hour. ~24 rows per device per day."
    ),
    "daily_stats": (
        "Pre-aggregated daily totals per device: total kWh, cost, CO\u2082, "
        "average wattage and peak hour. Prefer this over energy_readings for day-level analysis."
    ),
    "weekly_stats": (
        "Pre-aggregated weekly (ISO week) totals per device. "
        "Useful for week-over-week trend analysis."
    ),
    "monthly_stats": (
        "Pre-aggregated monthly totals per device. "
        "Useful for month-over-month and seasonal comparisons."
    ),
    "projections": (
        "End-of-day consumption forecasts generated mid-day, with 80% confidence interval "
        "bounds and projected cost. Compare projected_kwh vs daily_stats.total_kwh to assess accuracy."
    ),
    "user_sessions": (
        "App login and usage sessions per user: device type (ios/android/web), "
        "session duration, app version, screens visited and interaction count."
    ),
    "support_conversations": (
        "Customer support tickets opened by users. "
        "Contains subject, lifecycle status (open/waiting/resolved) and satisfaction score (1\u20135)."
    ),
    "support_messages": (
        "Individual messages within a support conversation. "
        "Role can be 'user', 'bot' (automated first response) or 'agent' (human support)."
    ),
}

COLUMN_DESCRIPTIONS = {
    "users": {
        "id": "Primary key",
        "username": "Unique login handle",
        "email": "Contact email address",
        "first_name": "Given name",
        "last_name": "Family name",
        "phone": "Optional phone number (may be NULL)",
        "country": "ISO 3166-1 alpha-2 code: NL, DE, BE, FR, SE, DK",
        "city": "City of residence",
        "locale": "Language/locale tag e.g. en-NL, de-DE",
        "is_premium": "1 = paid Premium subscriber, 0 = free tier",
        "registered_at": "Account creation timestamp (UTC ISO-8601)",
        "last_active_at": "Timestamp of last app session end (UTC). Derived from user_sessions.",
        "is_active": "1 = account enabled (Django flag)",
        "is_staff": "1 = admin user — exclude from business analysis with: WHERE is_staff=0 AND is_superuser=0",
        "date_joined": "Django built-in registration timestamp (same as registered_at)",
    },
    "homes": {
        "id": "Primary key",
        "user_id": "FK \u2192 users.id",
        "address": "Street address",
        "city": "City",
        "country": "ISO country code (same as users.country for that user)",
        "postal_code": "Postal / ZIP code",
        "home_type": "apartment | terraced | semi_detached | detached | studio",
        "floor_area_m2": "Floor area in square metres",
        "num_residents": "Number of occupants — positively correlated with consumption",
        "has_solar_panels": "1 = solar panels installed; these homes may show lower net consumption",
        "build_year": "Construction year — older homes tend to be less energy-efficient",
    },
    "devices": {
        "id": "Primary key",
        "home_id": "FK \u2192 homes.id",
        "serial_number": "Unique hardware serial in MSN-XXXXX-CC format",
        "model": "Hardware model: Homa Tracker v1 | v2 | Pro",
        "firmware_version": "Installed firmware version string",
        "installed_at": "Activation / installation date",
        "last_seen_at": "Last successful data transmission timestamp",
        "status": "active | inactive | error",
        "tariff_per_kwh": "Energy tariff in \u20ac/kWh used for cost calculations — set from energy_prices at install time",
        "p1_port_enabled": "1 = P1 smart-meter port active and streaming data",
    },
    "energy_prices": {
        "id": "Primary key",
        "country": "ISO country code this tariff applies to",
        "provider": "Energy supplier name",
        "tariff_type": "fixed | dynamic | off_peak",
        "price_per_kwh_eur": "Price in \u20ac per kWh",
        "valid_from": "Date this tariff became effective",
        "valid_to": "Date this tariff was superseded (NULL = currently active rate)",
        "source": "Data source / reference for this tariff",
    },
    "energy_readings": {
        "id": "Primary key",
        "device_id": "FK \u2192 devices.id",
        "recorded_at": "Timestamp of the reading — start of the measured hour (UTC ISO-8601)",
        "kwh": "Energy consumed in this one-hour window (kWh)",
        "watts_avg": "Average power draw during this hour (W)",
        "watts_peak": "Peak instantaneous power during this hour (W)",
        "co2_kg": "CO\u2082 emitted: kwh \u00d7 grid CO\u2082 factor (kg). Dutch grid: 0.389 kg/kWh",
        "cost_eur": "Cost for this hour: kwh \u00d7 devices.tariff_per_kwh (\u20ac)",
        "is_estimated": "1 = value was gap-filled/estimated; 0 = directly measured",
    },
    "daily_stats": {
        "id": "Primary key",
        "device_id": "FK \u2192 devices.id",
        "date": "Calendar date (YYYY-MM-DD)",
        "total_kwh": "Total energy consumed that day (kWh)",
        "total_cost_eur": "Total cost that day (\u20ac)",
        "total_co2_kg": "Total CO\u2082 that day (kg)",
        "avg_watts": "Average power draw across all 24 hours (W)",
        "peak_hour": "Hour-of-day (0\u201323) with the highest single-hour consumption",
        "peak_kwh": "kWh consumed in the peak hour",
    },
    "weekly_stats": {
        "id": "Primary key",
        "device_id": "FK \u2192 devices.id",
        "year": "Calendar year",
        "week_number": "ISO week number (1\u201353)",
        "total_kwh": "Total energy that week (kWh)",
        "total_cost_eur": "Total cost that week (\u20ac)",
        "total_co2_kg": "Total CO\u2082 that week (kg)",
        "avg_daily_kwh": "Average daily consumption within the week (kWh)",
    },
    "monthly_stats": {
        "id": "Primary key",
        "device_id": "FK \u2192 devices.id",
        "year": "Calendar year",
        "month": "Month number (1 = January \u2026 12 = December)",
        "total_kwh": "Total energy that month (kWh)",
        "total_cost_eur": "Total cost that month (\u20ac)",
        "total_co2_kg": "Total CO\u2082 that month (kg)",
        "avg_daily_kwh": "Average daily consumption within the month (kWh)",
    },
    "projections": {
        "id": "Primary key",
        "device_id": "FK \u2192 devices.id",
        "projection_date": "The calendar date being forecast (YYYY-MM-DD)",
        "projected_kwh": "Model\u2019s end-of-day kWh estimate",
        "lower_bound_kwh": "Lower bound of 80% confidence interval (kWh)",
        "upper_bound_kwh": "Upper bound of 80% confidence interval (kWh)",
        "projected_cost_eur": "Estimated total day cost (\u20ac)",
        "confidence_pct": "Model confidence score 0\u2013100",
        "created_at": "When this projection was generated (UTC)",
    },
    "user_sessions": {
        "id": "Primary key",
        "user_id": "FK \u2192 users.id",
        "started_at": "Session start timestamp (UTC ISO-8601)",
        "ended_at": "Session end timestamp (UTC), NULL if session still active",
        "duration_seconds": "Session length in seconds",
        "device_type": "ios | android | web",
        "app_version": "App version string at session time",
        "screens_visited": "Comma-separated list of screens the user navigated to",
        "actions_count": "Number of user interactions (taps / clicks) during the session",
    },
    "support_conversations": {
        "id": "Primary key",
        "user_id": "FK \u2192 users.id",
        "subject": "Conversation subject / topic (10 distinct topics in this dataset)",
        "status": "open | waiting | resolved",
        "created_at": "When the conversation was opened (UTC)",
        "resolved_at": "When the conversation was closed (UTC), NULL if still open",
        "satisfaction_score": "User satisfaction rating 1\u20135 after resolution. NULL if not yet rated.",
    },
    "support_messages": {
        "id": "Primary key",
        "conversation_id": "FK \u2192 support_conversations.id",
        "role": "user = customer message | bot = automated response | agent = human support staff",
        "message": "Full text of the message",
        "sent_at": "Message timestamp (UTC ISO-8601)",
        "is_read": "1 = message has been read by the recipient",
    },
}

# ── Safety ───────────────────────────────────────────────────────────────────

_BLOCKED = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|ATTACH|DETACH)\b"
    r"|PRAGMA\s+\w+\s*=",
    re.IGNORECASE,
)


def _validate(query: str) -> None:
    upper = query.lstrip().upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ValueError(
            "Only SELECT (and WITH … SELECT …) queries are allowed. "
            "This is a read-only analytical database."
        )
    if _BLOCKED.search(query):
        raise ValueError(
            "Query contains a write or structural keyword that is not permitted. "
            "Only read-only SELECT queries are allowed."
        )


def _conn() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Ensure homa_db.sqlite3 is in the homa-analyst/ folder."
        )
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_tables() -> list[dict]:
    """
    List all tables in the Homa Energy database with a short business
    description for each. Call this first to orient yourself before writing
    a query.
    """
    return [
        {"table": name, "description": desc}
        for name, desc in TABLE_DESCRIPTIONS.items()
    ]


@mcp.tool()
def describe_table(table_name: str) -> dict:
    """
    Return the column names, SQLite data types, and business descriptions
    for a specific table. Use this to confirm exact column names before
    writing a query.

    Args:
        table_name: Exact table name (e.g. 'daily_stats'). Use list_tables()
                    to see all available table names.
    """
    if table_name not in TABLE_DESCRIPTIONS:
        raise ValueError(
            f"Unknown table '{table_name}'. "
            f"Available: {', '.join(TABLE_DESCRIPTIONS)}"
        )
    conn = _conn()
    try:
        rows = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    finally:
        conn.close()

    col_meta = COLUMN_DESCRIPTIONS.get(table_name, {})
    return {
        "table": table_name,
        "description": TABLE_DESCRIPTIONS[table_name],
        "row_count_hint": "use: SELECT COUNT(*) FROM " + table_name,
        "columns": [
            {
                "column": r["name"],
                "type": r["type"],
                "not_null": bool(r["notnull"]),
                "primary_key": bool(r["pk"]),
                "description": col_meta.get(r["name"], ""),
            }
            for r in rows
        ],
    }


@mcp.tool()
def get_schema() -> dict:
    """
    Return a full overview of all tables, their columns and business
    descriptions in one call. Use this to understand the complete data
    model before writing a complex multi-table query.
    """
    return {
        name: {
            "description": TABLE_DESCRIPTIONS[name],
            "columns": COLUMN_DESCRIPTIONS.get(name, {}),
        }
        for name in TABLE_DESCRIPTIONS
    }


@mcp.tool()
def execute_query(query: str) -> dict:
    """
    Execute a read-only SQL SELECT query against the Homa Energy database.
    Results are capped at 500 rows. For large result sets, add a LIMIT
    clause or aggregate in the query itself.

    Args:
        query: A valid SQLite SELECT statement. WITH … SELECT … (CTEs) are
               also supported.

    Returns:
        A dict with keys: columns (list), rows (list of dicts), row_count (int),
        truncated (bool), and an optional truncation_note.
    """
    _validate(query)
    conn = _conn()
    try:
        cur = conn.execute(query)
        cols = [d[0] for d in (cur.description or [])]
        raw = cur.fetchmany(501)
        truncated = len(raw) > 500
        rows = raw[:500]
        return {
            "columns": cols,
            "rows": [dict(zip(cols, r)) for r in rows],
            "row_count": len(rows),
            "truncated": truncated,
            "truncation_note": (
                "Only the first 500 rows are returned. "
                "Add a LIMIT clause or aggregate further to reduce the result set."
                if truncated else None
            ),
        }
    except sqlite3.Error as exc:
        raise ValueError(f"SQL error: {exc}") from exc
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))
