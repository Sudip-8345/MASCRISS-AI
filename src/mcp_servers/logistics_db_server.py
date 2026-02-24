import json
import os
import sqlite3

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logistics.db")


def _init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id      TEXT PRIMARY KEY,
            supplier_name    TEXT NOT NULL,
            origin_port      TEXT NOT NULL,
            destination_port TEXT NOT NULL,
            status           TEXT NOT NULL,
            eta              TEXT NOT NULL
        )
        """
    )

    cur.execute("SELECT COUNT(*) FROM shipments")
    if cur.fetchone()[0] == 0:
        rows = [
            ("SH-001", "Foxconn Electronics",       "Shanghai",        "Los Angeles", "In Transit", "2026-03-05"),
            ("SH-002", "TechVision Components",      "Shenzhen",        "Rotterdam",   "In Transit", "2026-03-10"),
            ("SH-003", "Pacific Textiles",           "Ho Chi Minh City","Long Beach",  "Loading",    "2026-03-15"),
            ("SH-004", "Kanto Auto Parts",           "Yokohama",        "Vancouver",   "In Transit", "2026-03-02"),
            ("SH-005", "Samsung Display",            "Busan",           "Hamburg",      "In Transit", "2026-03-08"),
            ("SH-006", "BaoSteel Materials",         "Shanghai",        "Santos",       "Loading",    "2026-03-20"),
            ("SH-007", "Tata Chemicals",             "Mumbai",          "Felixstowe",  "In Transit", "2026-03-12"),
            ("SH-008", "Taiwan Semiconductor",       "Kaohsiung",       "Los Angeles",  "In Transit", "2026-03-06"),
            ("SH-009", "ZheJiang Textiles",          "Ningbo",          "New York",     "In Transit", "2026-03-14"),
            ("SH-010", "Hyundai Heavy Industries",   "Busan",           "Piraeus",      "Delayed",    "2026-03-01"),
            ("SH-011", "Reliance Industries",        "Mumbai",          "Houston",      "In Transit", "2026-03-18"),
            ("SH-012", "Mitsubishi Chemical",        "Yokohama",        "Long Beach",   "Loading",    "2026-03-22"),
        ]
        cur.executemany("INSERT INTO shipments VALUES (?,?,?,?,?,?)", rows)
        conn.commit()

    conn.close()


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
server = FastMCP(name="LogisticsDB")


@server.tool()
def query_shipments_by_region(region: str) -> str:
    """
    Find shipments whose origin port, destination port, or supplier name
    matches *region*.  Use this when a disruption is detected in a specific
    area and you need to know which cargo is affected.

    Args:
        region: Port city, country, or supplier keyword (e.g. "Shanghai").
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Return rows as dictionaries for easier JSON serialization
    cur = conn.cursor()

    like = f"%{region}%"
    cur.execute(
        "SELECT * FROM shipments WHERE origin_port LIKE ? "
        "OR destination_port LIKE ? OR supplier_name LIKE ?",
        (like, like, like),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not rows:
        return json.dumps({"message": f"No shipments found for '{region}'", "shipments": []})
    return json.dumps({"shipments": rows, "count": len(rows)})


@server.tool()
def query_all_shipments() -> str:
    """Return every shipment in the logistics database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Return rows as dictionaries for easier JSON serialization
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json.dumps({"shipments": rows, "count": len(rows)})


@server.tool()
def query_shipments_by_status(status: str) -> str:
    """
    Filter shipments by status.

    Args:
        status: One of "In Transit", "Loading", or "Delayed".
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Return rows as dictionaries for easier JSON serialization
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments WHERE status LIKE ?", (f"%{status}%",))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return json.dumps({"shipments": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _init_db()
    server.run(transport="stdio")