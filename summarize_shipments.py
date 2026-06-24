from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"a": SPREADSHEET_NS, "r": REL_NS}
EXCEL_DATE_BASE = dt.date(1899, 12, 30)

DETAIL_SHEET = "\u53d1\u8d27\u660e\u7ec6"
HISTORY_SHEET = "\u53d1\u8d27\u5386\u53f2\u8bb0\u5f55"
SHIPMENT_SHEETS = [HISTORY_SHEET, DETAIL_SHEET]
SHIP_DATE = "\u9001\u8d27\u65e5\u671f"
CUSTOMER = "\u5ba2\u6237\u7b80\u79f0"
INTERNAL_CODE = "\u5185\u90e8\u7f16\u7801"
MODEL_CANDIDATES = [
    "\u578b\u53f7",
    "\u578b   \u53f7",
    "\u54c1  \u540d",
    "\u54c1\u540d",
]
SPEC = "\u89c4   \u683c"
UNIT = "\u5355\u4f4d"
QUANTITY = "\u6570\u91cf"
PRICE = "\u5355\u4ef7"
AMOUNT = "\u91d1\u989d"
DELIVERY_NO = "\u9001\u8d27\u5355\n\u53f7\u7801"
ORDER_NO = "\u8ba2\u5355\u53f7\u7801"
NOTE = "\u5907\u6ce8"
PRODUCT_NAME_RULES = [{"model": "\u7eaf\u80f6\u819c", "use_spec_as_name": True}]
CUSTOMER_ALIASES: dict[str, str] = {}
MODEL_ALIASES: dict[str, str] = {}


@dataclass
class SummaryResult:
    date: dt.date
    sources: list[str]
    rows: list[dict]
    by_customer: list[dict]
    total_rows: int
    total_amount: float
    total_quantity: float
    customer_count: int


def excel_serial(value: dt.date) -> int:
    return (value - EXCEL_DATE_BASE).days


def parse_date(value) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return EXCEL_DATE_BASE + dt.timedelta(days=int(float(text)))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def to_number(value) -> float:
    if value in (None, ""):
        return 0.0
    text = str(value).replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def normalize_header(value) -> str:
    return str(value or "").replace(" ", "").replace("\n", "").strip()


def configure_business_rules(config: dict | None) -> None:
    global PRODUCT_NAME_RULES, CUSTOMER_ALIASES, MODEL_ALIASES
    if not config:
        return
    rules = config.get("product_name_rules")
    if isinstance(rules, list):
        PRODUCT_NAME_RULES = [rule for rule in rules if isinstance(rule, dict) and rule.get("model")]
    aliases = config.get("aliases") or {}
    CUSTOMER_ALIASES = {str(k).strip(): str(v).strip() for k, v in (aliases.get("customers") or {}).items()}
    MODEL_ALIASES = {str(k).strip(): str(v).strip() for k, v in (aliases.get("models") or {}).items()}


def apply_alias(value: str, aliases: dict[str, str]) -> str:
    text = (value or "").strip()
    return aliases.get(text, text)


def display_product_name(model: str, spec: str) -> str:
    model = (model or "").strip()
    spec = (spec or "").strip()
    for rule in PRODUCT_NAME_RULES:
        if normalize_header(model) == normalize_header(rule.get("model", "")) and rule.get("use_spec_as_name") and spec:
            return apply_alias(f"{model} / {spec}", MODEL_ALIASES)
    return apply_alias(model, MODEL_ALIASES)


def col_to_index(ref: str) -> int:
    letters = ""
    for ch in ref:
        if ch.isalpha():
            letters += ch.upper()
        else:
            break
    value = 0
    for ch in letters:
        value = value * 26 + ord(ch) - 64
    return value - 1


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("a:si", NS):
        strings.append("".join(node.text or "" for node in item.findall(".//a:t", NS)))
    return strings


def cell_value(cell, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//a:t", NS))
    node = cell.find("a:v", NS)
    if node is None:
        return ""
    value = node.text or ""
    if cell_type == "s" and value.isdigit():
        idx = int(value)
        return shared_strings[idx] if idx < len(shared_strings) else ""
    return value


def sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    relmap = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    out = {}
    for sheet in workbook.findall("a:sheets/a:sheet", NS):
        rid = sheet.attrib[f"{{{REL_NS}}}id"]
        target = relmap[rid].lstrip("/")
        out[sheet.attrib["name"]] = target if target.startswith("xl/") else f"xl/{target}"
    return out


def read_sheet_rows(path: Path, sheet_name: str = DETAIL_SHEET) -> list[list[str]]:
    with zipfile.ZipFile(path) as zf:
        paths = sheet_paths(zf)
        if sheet_name not in paths:
            raise ValueError(f"{path.name} missing sheet: {sheet_name}")
        shared_strings = read_shared_strings(zf)
        root = ET.fromstring(zf.read(paths[sheet_name]))
        rows = []
        for row in root.findall(".//a:sheetData/a:row", NS):
            values = []
            for cell in row.findall("a:c", NS):
                idx = col_to_index(cell.attrib.get("r", "A1"))
                while len(values) <= idx:
                    values.append("")
                values[idx] = cell_value(cell, shared_strings)
            rows.append(values)
        return rows


def find_header(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    for row_idx, row in enumerate(rows):
        normalized = [normalize_header(v) for v in row]
        if normalize_header(SHIP_DATE) in normalized and normalize_header(CUSTOMER) in normalized:
            return row_idx, {name: idx for idx, name in enumerate(normalized) if name}
    raise ValueError("No shipment-detail header row found")


def _pick_index(headers: dict[str, int], names: Iterable[str]) -> int | None:
    for name in names:
        idx = headers.get(normalize_header(name))
        if idx is not None:
            return idx
    return None


def _get(row: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    return row[idx]


def _shipment_indexes(headers: dict[str, int]) -> dict[str, int | None]:
    return {
        "customer": _pick_index(headers, [CUSTOMER]),
        "internal_code": _pick_index(headers, [INTERNAL_CODE]),
        "model": _pick_index(headers, MODEL_CANDIDATES),
        "spec": _pick_index(headers, [SPEC, "\u89c4\u683c"]),
        "unit": _pick_index(headers, [UNIT]),
        "quantity": _pick_index(headers, [QUANTITY]),
        "price": _pick_index(headers, [PRICE]),
        "amount": _pick_index(headers, [AMOUNT]),
        "ship_date": _pick_index(headers, [SHIP_DATE]),
        "delivery_no": _pick_index(headers, [DELIVERY_NO, "\u9001\u8d27\u5355\u53f7\u7801"]),
        "order_no": _pick_index(headers, [ORDER_NO]),
        "note": _pick_index(headers, [NOTE]),
    }


def _extract_shipments_from_sheet(path: Path, sheet_name: str) -> list[dict]:
    rows = read_sheet_rows(path, sheet_name)
    header_idx, headers = find_header(rows)
    idx = _shipment_indexes(headers)
    out = []
    for row in rows[header_idx + 1 :]:
        ship_date = parse_date(_get(row, idx["ship_date"]))
        if not ship_date:
            continue
        customer = apply_alias(_get(row, idx["customer"]).strip(), CUSTOMER_ALIASES)
        model = _get(row, idx["model"]).strip()
        amount = to_number(_get(row, idx["amount"]))
        quantity = to_number(_get(row, idx["quantity"]))
        if not customer and not model and not amount and not quantity:
            continue
        spec = _get(row, idx["spec"]).strip()
        out.append(
            {
                "\u9001\u8d27\u65e5\u671f": ship_date,
                "\u6765\u6e90\u6587\u4ef6": path.name,
                "\u5ba2\u6237": customer,
                "\u5185\u90e8\u7f16\u7801": _get(row, idx["internal_code"]).strip(),
                "\u578b\u53f7/\u54c1\u540d": display_product_name(model, spec),
                "\u89c4\u683c": spec,
                "\u5355\u4f4d": _get(row, idx["unit"]).strip(),
                "\u6570\u91cf": quantity,
                "\u5355\u4ef7": to_number(_get(row, idx["price"])),
                "\u91d1\u989d": amount,
                "\u9001\u8d27\u5355\u53f7": _get(row, idx["delivery_no"]).strip(),
                "\u8ba2\u5355\u53f7": _get(row, idx["order_no"]).strip(),
                "\u5907\u6ce8": _get(row, idx["note"]).strip(),
            }
        )
    return out


def _shipment_identity(row: dict) -> tuple:
    return (
        row.get("\u9001\u8d27\u65e5\u671f"),
        str(row.get("\u9001\u8d27\u5355\u53f7") or "").strip(),
        str(row.get("\u8ba2\u5355\u53f7") or "").strip(),
        str(row.get("\u5ba2\u6237") or "").strip(),
        str(row.get("\u5185\u90e8\u7f16\u7801") or "").strip(),
        str(row.get("\u578b\u53f7/\u54c1\u540d") or "").strip(),
        round(float(row.get("\u6570\u91cf") or 0), 6),
        round(float(row.get("\u91d1\u989d") or 0), 6),
    )


def extract_all_shipments(path: Path) -> list[dict]:
    rows = []
    seen = set()
    for sheet_name in SHIPMENT_SHEETS:
        try:
            sheet_rows = _extract_shipments_from_sheet(path, sheet_name)
        except ValueError:
            continue
        for row in sheet_rows:
            key = _shipment_identity(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    if not rows:
        rows = _extract_shipments_from_sheet(path, DETAIL_SHEET)
    return rows


def _row_date(row: dict) -> dt.date | None:
    value = row.get("\u9001\u8d27\u65e5\u671f")
    if isinstance(value, dt.date):
        return value
    return parse_date(value)


def summarize_rows(rows: Iterable[dict], target_date: dt.date, sources: Iterable[Path | str] | None = None) -> SummaryResult:
    filtered = [row for row in rows if _row_date(row) == target_date]
    filtered.sort(key=lambda r: (r["\u5ba2\u6237"], r["\u578b\u53f7/\u54c1\u540d"], r["\u9001\u8d27\u5355\u53f7"]))

    customer_map: dict[str, dict] = {}
    for row in filtered:
        key = row["\u5ba2\u6237"] or "\u672a\u586b\u5ba2\u6237"
        item = customer_map.setdefault(
            key,
            {"\u5ba2\u6237": key, "\u53d1\u8d27\u7b14\u6570": 0, "\u6570\u91cf": 0.0, "\u91d1\u989d": 0.0},
        )
        item["\u53d1\u8d27\u7b14\u6570"] += 1
        item["\u6570\u91cf"] += row["\u6570\u91cf"]
        item["\u91d1\u989d"] += row["\u91d1\u989d"]
    by_customer = sorted(customer_map.values(), key=lambda r: r["\u91d1\u989d"], reverse=True)

    return SummaryResult(
        date=target_date,
        sources=[str(p) for p in (sources or [])],
        rows=filtered,
        by_customer=by_customer,
        total_rows=len(filtered),
        total_amount=sum(r["\u91d1\u989d"] for r in filtered),
        total_quantity=sum(r["\u6570\u91cf"] for r in filtered),
        customer_count=len(customer_map),
    )


def extract_shipments(path: Path, target_date: dt.date) -> list[dict]:
    return summarize_rows(extract_all_shipments(path), target_date, [path]).rows


def summarize_sources(source_paths: Iterable[Path | str], target_date: dt.date) -> SummaryResult:
    sources = [Path(p) for p in source_paths]
    rows = []
    for path in sources:
        rows.extend(extract_all_shipments(path))
    return summarize_rows(rows, target_date, sources)


def fmt_num(value: float) -> str:
    if abs(value - round(value)) < 0.000001:
        return f"{value:,.0f}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def write_csv(result: SummaryResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "\u6765\u6e90\u6587\u4ef6",
        "\u5ba2\u6237",
        "\u578b\u53f7/\u54c1\u540d",
        "\u89c4\u683c",
        "\u5355\u4f4d",
        "\u6570\u91cf",
        "\u5355\u4ef7",
        "\u91d1\u989d",
        "\u9001\u8d27\u5355\u53f7",
        "\u8ba2\u5355\u53f7",
        "\u5907\u6ce8",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result.rows)


def table_html(rows: list[dict], fields: list[str]) -> str:
    head = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
    body = []
    for row in rows:
        cells = []
        for field in fields:
            value = row.get(field, "")
            if isinstance(value, float):
                value = fmt_num(value)
            cells.append(f"<td>{html.escape(str(value))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def write_html(result: SummaryResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    title = f"\u6bcf\u65e5\u53d1\u8d27\u6c47\u603b - {result.date:%Y-%m-%d}"
    detail_fields = [
        "\u5ba2\u6237",
        "\u578b\u53f7/\u54c1\u540d",
        "\u89c4\u683c",
        "\u5355\u4f4d",
        "\u6570\u91cf",
        "\u5355\u4ef7",
        "\u91d1\u989d",
        "\u9001\u8d27\u5355\u53f7",
        "\u8ba2\u5355\u53f7",
        "\u6765\u6e90\u6587\u4ef6",
    ]
    customer_fields = ["\u5ba2\u6237", "\u53d1\u8d27\u7b14\u6570", "\u6570\u91cf", "\u91d1\u989d"]
    source_list = "".join(f"<li>{html.escape(Path(src).name)}</li>" for src in result.sources)
    content = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 28px; color: #17202a; background: #f7f8fb; }}
h1 {{ font-size: 24px; margin: 0 0 16px; }}
h2 {{ font-size: 18px; margin: 28px 0 10px; }}
.cards {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-bottom: 18px; }}
.card {{ background: #fff; border: 1px solid #dde3ea; border-radius: 8px; padding: 14px; }}
.label {{ color: #667085; font-size: 13px; }}
.value {{ margin-top: 6px; font-size: 22px; font-weight: 700; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #dde3ea; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid #e7ebf0; text-align: left; font-size: 13px; vertical-align: top; }}
th {{ background: #edf2f7; font-weight: 700; position: sticky; top: 0; }}
tr:nth-child(even) td {{ background: #fbfcfe; }}
ul {{ margin-top: 6px; }}
@media (max-width: 900px) {{ .cards {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }} body {{ margin: 14px; }} }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<div class="cards">
  <div class="card"><div class="label">\u53d1\u8d27\u7b14\u6570</div><div class="value">{result.total_rows}</div></div>
  <div class="card"><div class="label">\u5ba2\u6237\u6570</div><div class="value">{result.customer_count}</div></div>
  <div class="card"><div class="label">\u603b\u6570\u91cf</div><div class="value">{fmt_num(result.total_quantity)}</div></div>
  <div class="card"><div class="label">\u603b\u91d1\u989d</div><div class="value">{fmt_num(result.total_amount)}</div></div>
</div>
<h2>\u6309\u5ba2\u6237\u6c47\u603b</h2>
{table_html(result.by_customer, customer_fields)}
<h2>\u53d1\u8d27\u660e\u7ec6</h2>
{table_html(result.rows, detail_fields)}
<h2>\u6570\u636e\u6765\u6e90</h2>
<ul>{source_list}</ul>
</body>
</html>"""
    path.write_text(content, encoding="utf-8")


def write_manifest(result: SummaryResult, csv_path: Path, html_path: Path, manifest_path: Path) -> None:
    manifest_path.write_text(
        json.dumps(
            {
                "date": result.date.isoformat(),
                "rows": result.total_rows,
                "customers": result.customer_count,
                "amount": result.total_amount,
                "csv": str(csv_path),
                "html": str(html_path),
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def default_sources() -> list[Path]:
    desktop = Path(r"C:\Users\Administrator\Desktop")
    needle = "\u53d1\u8d27\u7edf\u8ba1\u8868"
    return sorted(p for p in desktop.glob("*.xlsx") if "2026" in p.name and needle in p.name)


def run(config_path: Path | None, target_date: dt.date, out_dir: Path) -> tuple[SummaryResult, Path, Path, Path]:
    sources = default_sources()
    if config_path and config_path.exists():
        config = load_config(config_path)
        configure_business_rules(config)
        sources = [Path(p) for p in config.get("sources", sources)]
        out_dir = Path(config.get("output_dir", out_dir))
    result = summarize_sources(sources, target_date)
    csv_path = out_dir / f"\u6bcf\u65e5\u53d1\u8d27\u6c47\u603b-{target_date:%Y-%m-%d}.csv"
    html_path = out_dir / f"\u6bcf\u65e5\u53d1\u8d27\u6c47\u603b-{target_date:%Y-%m-%d}.html"
    manifest_path = out_dir / f"daily-shipment-summary-{target_date:%Y-%m-%d}.json"
    write_csv(result, csv_path)
    write_html(result, html_path)
    write_manifest(result, csv_path, html_path, manifest_path)
    return result, csv_path, html_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("shipment_config.json"))
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    target_date = dt.date.fromisoformat(args.date)
    result, csv_path, html_path, manifest_path = run(args.config, target_date, args.output_dir)
    print(f"date={target_date:%Y-%m-%d}")
    print(f"rows={result.total_rows}")
    print(f"customers={result.customer_count}")
    print(f"amount={result.total_amount:.2f}")
    print(f"csv={csv_path}")
    print(f"html={html_path}")
    print(f"manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
