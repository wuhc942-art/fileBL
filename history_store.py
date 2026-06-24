from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from pathlib import Path


DATE = "\u9001\u8d27\u65e5\u671f"
SOURCE = "\u6765\u6e90\u6587\u4ef6"
CUSTOMER = "\u5ba2\u6237"
INTERNAL_CODE = "\u5185\u90e8\u7f16\u7801"
MODEL = "\u578b\u53f7/\u54c1\u540d"
SPEC = "\u89c4\u683c"
UNIT = "\u5355\u4f4d"
QUANTITY = "\u6570\u91cf"
PRICE = "\u5355\u4ef7"
AMOUNT = "\u91d1\u989d"
DELIVERY_NO = "\u9001\u8d27\u5355\u53f7"
ORDER_NO = "\u8ba2\u5355\u53f7"
NOTE = "\u5907\u6ce8"


FIELDS = [
    DATE,
    SOURCE,
    CUSTOMER,
    INTERNAL_CODE,
    MODEL,
    SPEC,
    UNIT,
    QUANTITY,
    PRICE,
    AMOUNT,
    DELIVERY_NO,
    ORDER_NO,
    NOTE,
]


def _date_text(value) -> str:
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value or "").strip()


def _text(value) -> str:
    return str(value or "").strip()


def _number(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _row_uid(row: dict) -> str:
    parts = [
        _date_text(row.get(DATE)),
        _text(row.get(DELIVERY_NO)),
        _text(row.get(CUSTOMER)),
        _text(row.get(MODEL)),
        f"{_number(row.get(QUANTITY)):.6f}",
        f"{_number(row.get(AMOUNT)):.6f}",
        _text(row.get(SOURCE)),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                uid TEXT PRIMARY KEY,
                ship_date TEXT NOT NULL,
                source TEXT,
                customer TEXT,
                internal_code TEXT,
                model TEXT,
                spec TEXT,
                unit TEXT,
                quantity REAL,
                price REAL,
                amount REAL,
                delivery_no TEXT,
                order_no TEXT,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shipments_date ON shipments(ship_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shipments_customer ON shipments(customer)")
        conn.commit()
    finally:
        conn.close()


def save_history_rows(db_path: Path, rows: list[dict]) -> int:
    ensure_schema(db_path)
    inserted = 0
    conn = sqlite3.connect(db_path)
    try:
        for row in rows:
            ship_date = _date_text(row.get(DATE))
            if not ship_date:
                continue
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO shipments (
                    uid, ship_date, source, customer, internal_code, model, spec, unit,
                    quantity, price, amount, delivery_no, order_no, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _row_uid(row),
                    ship_date,
                    _text(row.get(SOURCE)),
                    _text(row.get(CUSTOMER)),
                    _text(row.get(INTERNAL_CODE)),
                    _text(row.get(MODEL)),
                    _text(row.get(SPEC)),
                    _text(row.get(UNIT)),
                    _number(row.get(QUANTITY)),
                    _number(row.get(PRICE)),
                    _number(row.get(AMOUNT)),
                    _text(row.get(DELIVERY_NO)),
                    _text(row.get(ORDER_NO)),
                    _text(row.get(NOTE)),
                ),
            )
            inserted += cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    return inserted


def load_history_rows(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    ensure_schema(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        records = [dict(record) for record in conn.execute(
            """
            SELECT ship_date, source, customer, internal_code, model, spec, unit,
                   quantity, price, amount, delivery_no, order_no, note
            FROM shipments
            ORDER BY ship_date, customer, model, delivery_no
            """
        ).fetchall()]
    finally:
        conn.close()
    rows = []
    for record in records:
        rows.append(
            {
                DATE: dt.date.fromisoformat(record["ship_date"]),
                SOURCE: record["source"] or "",
                CUSTOMER: record["customer"] or "",
                INTERNAL_CODE: record["internal_code"] or "",
                MODEL: record["model"] or "",
                SPEC: record["spec"] or "",
                UNIT: record["unit"] or "",
                QUANTITY: float(record["quantity"] or 0),
                PRICE: float(record["price"] or 0),
                AMOUNT: float(record["amount"] or 0),
                DELIVERY_NO: record["delivery_no"] or "",
                ORDER_NO: record["order_no"] or "",
                NOTE: record["note"] or "",
            }
        )
    return rows
