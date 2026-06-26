from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
import mimetypes
import os
import shutil
import sys
import tempfile
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from history_store import load_history_rows, save_history_rows
from material_catalog import classify_material, load_material_catalog
from summarize_shipments import (
    DETAIL_SHEET,
    HISTORY_SHEET,
    SHIP_DATE,
    SHIPMENT_SHEETS,
    SummaryResult,
    configure_business_rules,
    extract_all_shipments,
    find_header,
    load_config,
    normalize_header,
    parse_date,
    read_sheet_rows,
    summarize_rows,
    summarize_sources,
)


def _app_root() -> Path:
    configured = os.environ.get("SHIPMENT_APP_ROOT")
    if configured:
        return Path(configured).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = _app_root()
STATIC_DIR = ROOT / "web"
STORAGE_ROOT = Path(os.environ.get("SHIPMENT_DATA_ROOT") or ROOT).resolve()
UPLOAD_DIR = STORAGE_ROOT / "uploads"
REPORT_DIR = STORAGE_ROOT / "reports"
DATA_DIR = STORAGE_ROOT / "data"
HISTORY_DB = DATA_DIR / "history.sqlite"
APP_CONFIG = load_config(ROOT / "shipment_config.json") if (ROOT / "shipment_config.json").exists() else {}
configure_business_rules(APP_CONFIG)
HIGH_VALUE_THRESHOLD = float(APP_CONFIG.get("high_value_threshold", 100000))
APP_VERSION = "v1.0.4"
DEFAULT_MATERIAL_CATEGORIES = [
    {"name": "补强", "keywords": ["补强", "FR4", "钢片", "PI补强"]},
    {"name": "覆盖膜", "keywords": ["覆盖膜", "保护膜", "CVL"]},
    {"name": "基材", "keywords": ["基材", "铜箔", "FCCL", "PI基材"]},
]
MATERIAL_CATEGORIES = APP_CONFIG.get("material_categories") or DEFAULT_MATERIAL_CATEGORIES
MATERIAL_CATALOG_PATH = Path(os.environ.get("SHIPMENT_MATERIAL_CATALOG") or "").resolve() if os.environ.get("SHIPMENT_MATERIAL_CATALOG") else None
MATERIAL_CATALOG = load_material_catalog(MATERIAL_CATALOG_PATH) if MATERIAL_CATALOG_PATH and MATERIAL_CATALOG_PATH.exists() else {}
MATERIAL_CLASSIFICATION_CACHE: dict[tuple[str, str], str] = {}


def _round(value: float) -> float:
    return round(float(value or 0), 2)


def _classify_material_category(model: str, spec: str = "") -> str:
    key = (str(model or ""), str(spec or ""))
    category = MATERIAL_CLASSIFICATION_CACHE.get(key)
    if category is None:
        category = classify_material(model, spec, MATERIAL_CATALOG, MATERIAL_CATEGORIES)
        MATERIAL_CLASSIFICATION_CACHE[key] = category
    return category


def configure_material_catalog(path: Path | str | None) -> dict:
    global MATERIAL_CATALOG_PATH, MATERIAL_CATALOG
    MATERIAL_CATALOG_PATH = Path(path).resolve() if path else None
    MATERIAL_CATALOG = load_material_catalog(MATERIAL_CATALOG_PATH) if MATERIAL_CATALOG_PATH and MATERIAL_CATALOG_PATH.exists() else {}
    MATERIAL_CLASSIFICATION_CACHE.clear()
    return {
        "materialCatalogPath": str(MATERIAL_CATALOG_PATH) if MATERIAL_CATALOG_PATH else "",
        "materialCatalogRows": len(MATERIAL_CATALOG),
    }


def _amount_breakdown_by_key(rows: list[dict], key: str) -> list[dict]:
    grouped: dict[str, dict] = {}
    total = sum(float(row.get("amount") or 0) for row in rows)
    for row in rows:
        name = str(row.get(key) or "其他").strip() or "其他"
        item = grouped.setdefault(name, {"name": name, "amount": 0.0, "quantity": 0.0, "rows": 0})
        item["amount"] += float(row.get("amount") or 0)
        item["quantity"] += float(row.get("quantity") or 0)
        item["rows"] += 1
    output = sorted(grouped.values(), key=lambda item: item["amount"], reverse=True)
    for item in output:
        item["amount"] = _round(item["amount"])
        item["quantity"] = _round(item["quantity"])
        item["share"] = _round(item["amount"] / total * 100) if total else 0
    return output


def _customer_material_breakdown(rows: list[dict], customer: str) -> list[dict]:
    return _amount_breakdown_by_key([row for row in rows if row.get("customer") == customer], "materialCategory")


def configure_storage_root(storage_root: Path | str, migrate_from: Path | None = None) -> dict:
    global STORAGE_ROOT, UPLOAD_DIR, REPORT_DIR, DATA_DIR, HISTORY_DB
    new_root = Path(storage_root).resolve()
    old_history = HISTORY_DB
    if migrate_from is not None:
        old_history = Path(migrate_from).resolve() / "data" / "history.sqlite"

    STORAGE_ROOT = new_root
    UPLOAD_DIR = STORAGE_ROOT / "uploads"
    REPORT_DIR = STORAGE_ROOT / "reports"
    DATA_DIR = STORAGE_ROOT / "data"
    HISTORY_DB = DATA_DIR / "history.sqlite"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if old_history.exists() and old_history.resolve() != HISTORY_DB.resolve() and not HISTORY_DB.exists():
        shutil.copy2(old_history, HISTORY_DB)

    return {
        "storageRoot": str(STORAGE_ROOT),
        "dataDir": str(DATA_DIR),
        "reportDir": str(REPORT_DIR),
        "uploadDir": str(UPLOAD_DIR),
        "historyDb": str(HISTORY_DB),
    }


def readonly_mode() -> bool:
    return os.environ.get("SHIPMENT_PUBLIC_READONLY", "").strip().lower() in {"1", "true", "yes", "on"}


def admin_token() -> str:
    return os.environ.get("SHIPMENT_ADMIN_TOKEN", "").strip()


def is_write_allowed(readonly: bool, admin_token: str, headers: dict, query: dict) -> bool:
    if not readonly:
        return True
    if not admin_token:
        return False
    header_token = ""
    for key, value in headers.items():
        if str(key).lower() == "x-admin-token":
            header_token = str(value)
            break
    query_token = query.get("adminToken", [""])[0] if query else ""
    return header_token == admin_token or query_token == admin_token


def _build_payload_from_rows(rows: list[dict], target_date: dt.date, sources: list[Path | str]) -> dict:
    result = summarize_rows(rows, target_date, sources)
    reference_results = _build_reference_results(rows, target_date, sources)
    history_context = _build_history_context(rows, target_date)
    payload = build_dashboard_payload(result, reference_results, history_context)
    history_rows = [
        row
        for row in rows
        if (parse_date(row.get(SHIP_DATE)) or dt.date.max) <= target_date
    ]
    history_frontend_rows = _frontend_rows(history_rows)
    payload["customerHistoryProfiles"] = _build_customer_profiles(history_frontend_rows)
    payload["customerHistoryDetails"] = {}
    return payload


def _safe_export_name(filename: str) -> str:
    name = Path(filename or "export.txt").name
    return "".join(ch for ch in name if ch not in '<>:"/\\|?*').strip() or "export.txt"


def save_export_file(report_dir: Path, filename: str, content: str, encoding: str = "text") -> dict:
    export_dir = report_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    target = export_dir / _safe_export_name(filename)
    if encoding == "base64":
        target.write_bytes(base64.b64decode(content))
    else:
        target.write_text(content, encoding="utf-8-sig")
    return {"path": str(target), "directory": str(export_dir), "filename": target.name}


def _source_check(path: Path, target_date: dt.date) -> dict:
    check = {
        "file": path.name,
        "status": "ready",
        "messages": [],
        "hasDetailSheet": False,
        "hasHistorySheet": False,
        "hasDateColumn": False,
        "monthMatched": False,
        "sheets": {},
    }
    for sheet_name in SHIPMENT_SHEETS:
        sheet_check = {
            "hasSheet": False,
            "hasDateColumn": False,
            "monthMatched": False,
            "message": "",
        }
        try:
            rows = read_sheet_rows(path, sheet_name)
            sheet_check["hasSheet"] = True
            header_idx, headers = find_header(rows)
            sheet_check["hasDateColumn"] = normalize_header(SHIP_DATE) in headers
            dates = []
            ship_date_idx = headers.get(normalize_header(SHIP_DATE))
            if ship_date_idx is not None:
                for row in rows[header_idx + 1 :]:
                    if ship_date_idx < len(row):
                        parsed = parse_date(row[ship_date_idx])
                        if parsed:
                            dates.append(parsed)
            sheet_check["monthMatched"] = any(
                date.year == target_date.year and date.month == target_date.month for date in dates
            )
            if not sheet_check["hasDateColumn"]:
                sheet_check["message"] = "未识别到送货日期列"
            elif not sheet_check["monthMatched"]:
                sheet_check["message"] = "未发现统计月份内的送货日期"
            else:
                sheet_check["message"] = "检查通过"
        except Exception as exc:
            sheet_check["message"] = str(exc)
        check["sheets"][sheet_name] = sheet_check

    history_check = check["sheets"].get(HISTORY_SHEET, {})
    detail_check = check["sheets"].get(DETAIL_SHEET, {})
    check["hasHistorySheet"] = bool(history_check.get("hasSheet"))
    check["hasDetailSheet"] = bool(detail_check.get("hasSheet"))
    check["hasDateColumn"] = any(item.get("hasDateColumn") for item in check["sheets"].values())
    check["monthMatched"] = any(item.get("monthMatched") for item in check["sheets"].values())

    missing_sheets = [name for name, item in check["sheets"].items() if not item.get("hasSheet")]
    readable_sheets = [item for item in check["sheets"].values() if item.get("hasSheet") and item.get("hasDateColumn")]
    if not readable_sheets:
        check["status"] = "error"
        check["messages"].append("未找到可读取的发货工作表，请确认包含“发货历史记录”或“发货明细”，且有“送货日期”列。")
    elif missing_sheets:
        check["status"] = "warning"
        check["messages"].append(f"缺少工作表：{'、'.join(missing_sheets)}")
    if not check["monthMatched"]:
        if check["status"] != "error":
            check["status"] = "warning"
        check["messages"].append("未发现统计月份内的送货日期，请核对统计日期。")
    if not check["messages"]:
        check["messages"].append("文件结构检查通过")
    return check


def _build_import_checks(sources: list[str], target_date: dt.date) -> dict:
    files = [_source_check(Path(source), target_date) for source in sources]
    error_count = sum(1 for item in files if item["status"] == "error")
    warning_count = sum(1 for item in files if item["status"] == "warning")
    status = "error" if error_count else "warning" if warning_count else "ready"
    return {
        "status": status,
        "errorCount": error_count,
        "warningCount": warning_count,
        "files": files,
    }


def _build_import_summary(read_rows: int, inserted_rows: int, errors: list[dict] | None = None) -> dict:
    errors = errors or []
    read_rows = int(read_rows or 0)
    inserted_rows = int(inserted_rows or 0)
    skipped_rows = max(0, read_rows - inserted_rows)
    parts = [
        f"读取 {read_rows} 条",
        f"新增 {inserted_rows} 条",
        f"跳过重复 {skipped_rows} 条",
    ]
    if errors:
        parts.append(f"错误 {len(errors)} 个文件")
    return {
        "readRows": read_rows,
        "insertedRows": inserted_rows,
        "skippedDuplicateRows": skipped_rows,
        "errorRows": len(errors),
        "errors": errors,
        "message": "，".join(parts) + "。",
    }


def _group(rows: list[dict], key: str, limit: int = 10) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        name = str(row.get(key) or "未填写").strip() or "未填写"
        item = grouped.setdefault(name, {"name": name, "rows": 0, "quantity": 0.0, "amount": 0.0})
        item["rows"] += 1
        item["quantity"] += float(row.get("数量") or 0)
        item["amount"] += float(row.get("金额") or 0)
    ranked = sorted(grouped.values(), key=lambda item: item["amount"], reverse=True)
    for item in ranked:
        item["quantity"] = _round(item["quantity"])
        item["amount"] = _round(item["amount"])
    return ranked[:limit]


def _dedupe_key(row: dict) -> tuple:
    return (
        str(row.get("送货单号") or "").strip(),
        str(row.get("客户") or "").strip(),
        str(row.get("型号/品名") or "").strip(),
        _round(row.get("数量", 0)),
        _round(row.get("金额", 0)),
    )


def _duplicate_keys(rows: list[dict]) -> set[tuple]:
    counts: dict[tuple, int] = {}
    for row in rows:
        key = _dedupe_key(row)
        if not any(key):
            continue
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _anomaly_flags(row: dict, duplicate_keys: set[tuple] | None = None) -> list[str]:
    flags = []
    if not str(row.get("客户") or "").strip():
        flags.append("missingCustomer")
    if not str(row.get("型号/品名") or "").strip():
        flags.append("missingModel")
    if float(row.get("数量") or 0) == 0:
        flags.append("zeroQuantity")
    if float(row.get("数量") or 0) < 0:
        flags.append("negativeQuantity")
    if float(row.get("金额") or 0) == 0:
        flags.append("zeroAmount")
    if float(row.get("金额") or 0) < 0:
        flags.append("negativeAmount")
    if not str(row.get("送货单号") or "").strip():
        flags.append("missingDeliveryNo")
    if float(row.get("单价") or 0) == 0:
        flags.append("missingPrice")
    if duplicate_keys and _dedupe_key(row) in duplicate_keys:
        flags.append("duplicateShipment")
    return flags


def _build_anomalies(rows: list[dict]) -> dict:
    labels = {
        "missingCustomer": "空客户",
        "missingModel": "空型号",
        "zeroQuantity": "数量为 0",
        "zeroAmount": "金额为 0",
        "negativeAmount": "金额为负",
        "negativeQuantity": "数量为负",
        "missingDeliveryNo": "缺送货单号",
        "missingPrice": "缺单价",
        "duplicateShipment": "疑似重复",
    }
    counts = {key: 0 for key in labels}
    items = []
    duplicates = _duplicate_keys(rows)
    for index, row in enumerate(rows):
        flags = _anomaly_flags(row, duplicates)
        if not flags:
            continue
        for flag in flags:
            counts[flag] += 1
        items.append(
            {
                "rowIndex": index,
                "customer": row.get("客户", ""),
                "model": row.get("型号/品名", ""),
                "amount": _round(row.get("金额", 0)),
                "quantity": _round(row.get("数量", 0)),
                "deliveryNo": row.get("送货单号", ""),
                "flags": flags,
                "labels": [labels[flag] for flag in flags],
            }
        )
    return {"total": sum(counts.values()), "counts": counts, "items": items}


def _build_file_check(sources: list[str]) -> dict:
    actual = len(sources)
    status = "ready"
    message = f"已上传 {actual} 个文件，将合并读取每个文件中的发货明细。"
    return {
        "expected": None,
        "actual": actual,
        "status": status,
        "message": message,
        "files": [Path(source).name for source in sources],
    }


def _build_insights(result: SummaryResult, customer_rows: list[dict], model_rows: list[dict], anomalies: dict) -> list[str]:
    insights = []
    if result.total_rows == 0:
        return ["当前日期没有发货记录，请确认统计日期和上传文件是否正确。"]
    insights.append(
        f"今日共 {result.total_rows} 笔发货，涉及 {result.customer_count} 个客户，总金额 {result.total_amount:,.2f}。"
    )
    if customer_rows:
        top = customer_rows[0]
        share = (top["amount"] / result.total_amount * 100) if result.total_amount else 0
        insights.append(f"金额最高客户是 {top['name']}，金额 {top['amount']:,.2f}，占今日总额 {share:.1f}%。")
    if model_rows:
        top = model_rows[0]
        insights.append(f"金额最高型号/品名是 {top['name']}，共 {top['rows']} 笔，金额 {top['amount']:,.2f}。")
    if anomalies.get("total", 0):
        insights.append(f"发现 {anomalies['total']} 个异常提醒，建议先查看异常筛选后再导出日报。")
    else:
        insights.append("未发现金额为 0、负数量、缺单号或缺单价的异常提醒。")
    return insights


def _metric_snapshot(result: SummaryResult) -> dict:
    return {
        "rows": result.total_rows,
        "amount": _round(result.total_amount),
        "quantity": _round(result.total_quantity),
        "customers": result.customer_count,
    }


def _compare_value(current: float, baseline: float) -> dict:
    baseline = _round(baseline)
    current = _round(current)
    delta = _round(current - baseline)
    return {
        "current": current,
        "baseline": baseline,
        "delta": delta,
        "percent": _round(delta / baseline * 100) if baseline else None,
        "hasBaseline": True,
    }


def _build_comparisons(result: SummaryResult, reference_results: dict[str, SummaryResult] | None) -> dict:
    reference_results = reference_results or {}
    current = _metric_snapshot(result)
    comparisons = {}
    for key, reference in reference_results.items():
        baseline = _metric_snapshot(reference)
        comparisons[key] = {
            "date": reference.date.isoformat(),
            "amount": _compare_value(current["amount"], baseline["amount"]),
            "quantity": _compare_value(current["quantity"], baseline["quantity"]),
            "customers": _compare_value(current["customers"], baseline["customers"]),
        }
    return comparisons


def _average_result(all_rows: list[dict], target_date: dt.date, days: int, sources: list[Path | str]) -> SummaryResult:
    daily = [
        summarize_rows(all_rows, target_date - dt.timedelta(days=offset), sources)
        for offset in range(1, days + 1)
    ]
    return SummaryResult(
        date=target_date - dt.timedelta(days=days),
        sources=[str(source) for source in sources],
        rows=[],
        by_customer=[],
        total_rows=sum(item.total_rows for item in daily) / days if days else 0,
        total_amount=sum(item.total_amount for item in daily) / days if days else 0,
        total_quantity=sum(item.total_quantity for item in daily) / days if days else 0,
        customer_count=sum(item.customer_count for item in daily) / days if days else 0,
    )


def _build_reference_results(all_rows: list[dict], target_date: dt.date, sources: list[Path | str]) -> dict[str, SummaryResult]:
    return {
        "yesterday": summarize_rows(all_rows, target_date - dt.timedelta(days=1), sources),
        "lastWeek": summarize_rows(all_rows, target_date - dt.timedelta(days=7), sources),
        "last7Average": _average_result(all_rows, target_date, 7, sources),
        "last30Average": _average_result(all_rows, target_date, 30, sources),
    }


def _build_history_context(all_rows: list[dict], target_date: dt.date, active_days: int = 30, dormant_days: int = 14) -> dict:
    customer_dates: dict[str, list[dt.date]] = {}
    for row in all_rows:
        customer = str(row.get("客户") or "").strip()
        ship_date = row.get("送货日期")
        if not customer or not isinstance(ship_date, dt.date):
            continue
        customer_dates.setdefault(customer, []).append(ship_date)

    today_customers = {
        customer
        for customer, dates in customer_dates.items()
        if any(ship_date == target_date for ship_date in dates)
    }
    known_before = {
        customer
        for customer, dates in customer_dates.items()
        if any(ship_date < target_date for ship_date in dates)
    }
    active_start = target_date - dt.timedelta(days=active_days)
    active_before = {
        customer
        for customer, dates in customer_dates.items()
        if any(active_start <= ship_date < target_date for ship_date in dates)
    }
    returning = []
    at_risk = []
    for customer, dates in customer_dates.items():
        previous_dates = [ship_date for ship_date in dates if ship_date < target_date]
        if not previous_dates:
            continue
        last_before = max(previous_dates)
        quiet_days = (target_date - last_before).days
        if customer in today_customers and quiet_days >= dormant_days:
            returning.append(customer)
        if customer not in today_customers and quiet_days >= dormant_days:
            at_risk.append(customer)

    return {
        "knownCustomersBefore": sorted(known_before),
        "activeCustomersBefore": sorted(active_before),
        "returningCustomers": sorted(returning),
        "atRiskCustomers": sorted(at_risk),
    }


def _build_model_details(rows: list[dict]) -> dict[str, list[dict]]:
    details: dict[str, dict[str, dict]] = {}
    for row in rows:
        model = row.get("model") or "未填写型号"
        customer = row.get("customer") or "未填写客户"
        item = details.setdefault(model, {}).setdefault(
            customer,
            {"customer": customer, "rows": 0, "quantity": 0.0, "amount": 0.0},
        )
        item["rows"] += 1
        item["quantity"] += float(row.get("quantity") or 0)
        item["amount"] += float(row.get("amount") or 0)
    output = {}
    for model, customer_map in details.items():
        output[model] = sorted(
            (
                {
                    "customer": item["customer"],
                    "rows": item["rows"],
                    "quantity": _round(item["quantity"]),
                    "amount": _round(item["amount"]),
                }
                for item in customer_map.values()
            ),
            key=lambda item: item["amount"],
            reverse=True,
        )
    return output


def _classify_tax_type(source: str) -> str:
    if "现金" in source:
        return "现金"
    if "含税" in source:
        return "含税"
    return "未分类"


def _classify_company(source: str) -> str:
    if "科泰顺" in source:
        return "科泰顺"
    if "奥科泰" in source:
        return "奥科泰"
    return "其他"


def _amount_breakdown(rows: list[dict], classifier) -> list[dict]:
    grouped: dict[str, dict] = {}
    total = sum(float(row.get("amount") or 0) for row in rows)
    for row in rows:
        name = classifier(str(row.get("source") or ""))
        item = grouped.setdefault(name, {"name": name, "amount": 0.0, "rows": 0})
        item["amount"] += float(row.get("amount") or 0)
        item["rows"] += 1
    output = sorted(grouped.values(), key=lambda item: item["amount"], reverse=True)
    for item in output:
        item["amount"] = _round(item["amount"])
        item["share"] = _round(item["amount"] / total * 100) if total else 0
    return output


def _build_amount_structure(rows: list[dict]) -> dict:
    return {
        "taxType": _amount_breakdown(rows, _classify_tax_type),
        "company": _amount_breakdown(rows, _classify_company),
    }


def _customer_amounts(result: SummaryResult) -> dict[str, float]:
    return {row.get("客户", ""): float(row.get("金额") or 0) for row in result.by_customer}


def _frontend_rows(raw_rows: list[dict], duplicates: set[tuple] | None = None) -> list[dict]:
    duplicates = duplicates or set()
    return [
        {
            "source": row.get("来源文件", ""),
            "customer": row.get("客户", ""),
            "model": row.get("型号/品名", ""),
            "spec": row.get("规格", ""),
            "unit": row.get("单位", ""),
            "quantity": _round(row.get("数量", 0)),
            "price": _round(row.get("单价", 0)),
            "amount": _round(row.get("金额", 0)),
            "deliveryNo": row.get("送货单号", ""),
            "orderNo": row.get("订单号", ""),
            "note": row.get("备注", ""),
            "materialCategory": _classify_material_category(row.get("型号/品名", ""), row.get("规格", "")),
            "anomalies": _anomaly_flags(row, duplicates),
        }
        for row in raw_rows
    ]


def _build_customer_details(rows: list[dict]) -> dict[str, list[dict]]:
    customer_details: dict[str, list[dict]] = {}
    for row in rows:
        customer_details.setdefault(row["customer"] or "未填写客户", []).append(row)
    return customer_details


def _profile_breakdown(rows: list[dict], key: str) -> list[dict]:
    grouped: dict[str, dict] = {}
    total_amount = sum(float(row.get("amount") or 0) for row in rows)
    for row in rows:
        name = str(row.get(key) or ("其他" if key == "materialCategory" else "未填写型号")).strip()
        item = grouped.setdefault(name, {"name": name, "rows": 0, "quantity": 0.0, "amount": 0.0, "share": 0.0})
        item["rows"] += 1
        item["quantity"] += float(row.get("quantity") or 0)
        item["amount"] += float(row.get("amount") or 0)
    output = sorted(grouped.values(), key=lambda item: (item["amount"], item["quantity"], item["rows"]), reverse=True)
    for item in output:
        item["quantity"] = _round(item["quantity"])
        item["amount"] = _round(item["amount"])
        item["share"] = _round(item["amount"] / total_amount * 100) if total_amount else 0
    return output


def _build_customer_profiles(rows: list[dict]) -> dict[str, dict]:
    by_customer = _build_customer_details(rows)
    profiles: dict[str, dict] = {}
    for customer, customer_rows in by_customer.items():
        categories = _profile_breakdown(customer_rows, "materialCategory")
        models = _profile_breakdown(customer_rows, "model")
        profiles[customer] = {
            "total": {
                "rows": len(customer_rows),
                "quantity": _round(sum(float(row.get("quantity") or 0) for row in customer_rows)),
                "amount": _round(sum(float(row.get("amount") or 0) for row in customer_rows)),
            },
            "primaryCategory": categories[0] if categories else None,
            "primaryModel": models[0] if models else None,
            "categories": categories,
            "models": models,
        }
    return profiles


def _build_business_alerts(result: SummaryResult, reference_results: dict[str, SummaryResult] | None) -> dict:
    reference_results = reference_results or {}
    today_customers = set(_customer_amounts(result))
    reference_amounts: dict[str, float] = {}
    for reference in reference_results.values():
        for customer, amount in _customer_amounts(reference).items():
            reference_amounts[customer] = max(reference_amounts.get(customer, 0.0), amount)
    high_value_threshold = HIGH_VALUE_THRESHOLD
    high_value_customers = [
        {
            "customer": row.get("客户", ""),
            "amount": _round(row.get("金额", 0)),
            "quantity": _round(row.get("数量", 0)),
            "rows": row.get("发货笔数", 0),
        }
        for row in result.by_customer
        if float(row.get("金额") or 0) >= high_value_threshold
    ]
    new_customers = sorted(today_customers - set(reference_amounts))
    silent_customers = sorted(
        (set(reference_amounts) - today_customers),
        key=lambda customer: reference_amounts.get(customer, 0.0),
        reverse=True,
    )
    return {
        "highValueThreshold": high_value_threshold,
        "highValueCustomers": high_value_customers,
        "newCustomers": new_customers,
        "silentCustomers": silent_customers,
    }


def _build_business_alerts_with_history(
    result: SummaryResult,
    reference_results: dict[str, SummaryResult] | None,
    history_context: dict | None = None,
) -> dict:
    if not history_context:
        alerts = _build_business_alerts(result, reference_results)
        alerts["returningCustomers"] = []
        alerts["atRiskCustomers"] = []
        alerts["historyMode"] = False
        alerts["highValueThreshold"] = HIGH_VALUE_THRESHOLD
        return alerts

    today_customers = set(_customer_amounts(result))
    known_before = set(history_context.get("knownCustomersBefore") or [])
    active_before = set(history_context.get("activeCustomersBefore") or [])
    high_value_customers = [
        {
            "customer": row.get("\u5ba2\u6237", ""),
            "amount": _round(row.get("\u91d1\u989d", 0)),
            "quantity": _round(row.get("\u6570\u91cf", 0)),
            "rows": row.get("\u53d1\u8d27\u7b14\u6570", 0),
        }
        for row in result.by_customer
        if float(row.get("\u91d1\u989d") or 0) >= HIGH_VALUE_THRESHOLD
    ]
    return {
        "highValueThreshold": HIGH_VALUE_THRESHOLD,
        "highValueCustomers": high_value_customers,
        "newCustomers": sorted(today_customers - known_before),
        "silentCustomers": sorted(active_before - today_customers),
        "returningCustomers": sorted(history_context.get("returningCustomers") or []),
        "atRiskCustomers": sorted(history_context.get("atRiskCustomers") or []),
        "historyMode": True,
    }


def _extract_boundary(content_type: str) -> bytes | None:
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("boundary="):
            return part.split("=", 1)[1].strip('"').encode("utf-8")
    return None


def _iter_uploaded_parts(content_type: str, body: bytes):
    boundary = _extract_boundary(content_type)
    if not boundary:
        return
    marker = b"--" + boundary
    for raw in body.split(marker):
        raw = raw.strip()
        if not raw or raw == b"--":
            continue
        if raw.endswith(b"--"):
            raw = raw[:-2].strip()
        header_blob, sep, payload = raw.partition(b"\r\n\r\n")
        if not sep:
            header_blob, sep, payload = raw.partition(b"\n\n")
        if not sep:
            continue
        headers = header_blob.decode("utf-8", errors="replace")
        filename = None
        for header in headers.split("\r\n"):
            if "filename=" in header:
                filename = header.split("filename=", 1)[1].split(";", 1)[0].strip().strip('"')
                break
        if filename:
            if payload.endswith(b"\r\n"):
                payload = payload[:-2]
            elif payload.endswith(b"\n"):
                payload = payload[:-1]
            yield filename, payload


def build_dashboard_payload(
    result: SummaryResult,
    reference_results: dict[str, SummaryResult] | None = None,
    history_context: dict | None = None,
) -> dict:
    duplicates = _duplicate_keys(result.rows)
    rows = _frontend_rows(result.rows, duplicates)
    customers = [
        {
            "customer": row.get("客户", ""),
            "rows": row.get("发货笔数", 0),
            "quantity": _round(row.get("数量", 0)),
            "amount": _round(row.get("金额", 0)),
            "primaryMaterialCategory": (
                _customer_material_breakdown(rows, row.get("客户", ""))[0]["name"]
                if _customer_material_breakdown(rows, row.get("客户", ""))
                else "其他"
            ),
            "materialCategories": _customer_material_breakdown(rows, row.get("客户", "")),
        }
        for row in result.by_customer
    ]
    customer_details = _build_customer_details(rows)

    model_rows = _group(result.rows, "型号/品名", limit=10)
    source_rows = _group(result.rows, "来源文件", limit=10)
    anomalies = _build_anomalies(result.rows)
    file_check = _build_file_check(result.sources)
    customer_chart_rows = [
        {
            "name": row.get("客户", ""),
            "rows": row.get("发货笔数", 0),
            "quantity": _round(row.get("数量", 0)),
            "amount": _round(row.get("金额", 0)),
        }
        for row in result.by_customer[:10]
    ]

    return {
        "appVersion": APP_VERSION,
        "date": result.date.isoformat(),
        "sources": [Path(source).name for source in result.sources],
        "fileCheck": file_check,
        "importChecks": _build_import_checks(result.sources, result.date),
        "kpis": {
            "rows": result.total_rows,
            "customers": result.customer_count,
            "quantity": _round(result.total_quantity),
            "amount": _round(result.total_amount),
        },
        "charts": {
            "customers": customer_chart_rows,
            "models": model_rows,
            "sources": source_rows,
            "materialCategories": _amount_breakdown_by_key(rows, "materialCategory"),
        },
        "comparisons": _build_comparisons(result, reference_results),
        "modelDetails": _build_model_details(rows),
        "amountStructure": _build_amount_structure(rows),
        "businessAlerts": _build_business_alerts_with_history(result, reference_results, history_context),
        "anomalies": anomalies,
        "insights": _build_insights(result, customer_chart_rows, model_rows, anomalies),
        "customerDetails": customer_details,
        "customerHistoryDetails": customer_details,
        "customers": customers,
        "rows": rows,
    }


class ShipmentDashboardHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/history-summary":
            return self._history_summary(parsed)
        if parsed.path in ("/", "/index.html"):
            return self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.css":
            return self._send_file(STATIC_DIR / "app.css", "text/css; charset=utf-8")
        if parsed.path == "/comparison_logic.js":
            return self._send_file(STATIC_DIR / "comparison_logic.js", "text/javascript; charset=utf-8")
        if parsed.path == "/customer_profile.js":
            return self._send_file(STATIC_DIR / "customer_profile.js", "text/javascript; charset=utf-8")
        if parsed.path == "/app.js":
            return self._send_file(STATIC_DIR / "app.js", "text/javascript; charset=utf-8")
        return self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not is_write_allowed(readonly_mode(), admin_token(), dict(self.headers.items()), query):
            return self._send_json(
                {"error": "Public read-only mode is enabled. Admin token is required for uploads or report saving."},
                status=403,
            )
        if parsed.path == "/api/export-file":
            return self._export_file()
        if parsed.path == "/api/save-report":
            return self._save_report_package()
        if parsed.path != "/api/summarize":
            return self.send_error(404, "Not found")
        try:
            target_date = dt.date.fromisoformat(query.get("date", [dt.date.today().isoformat()])[0])
            paths = self._save_uploads()
            if not paths:
                raise ValueError("请至少上传一个 Excel 文件。")
            all_rows = []
            import_errors = []
            for path in paths:
                try:
                    all_rows.extend(extract_all_shipments(path))
                except Exception as exc:
                    import_errors.append({"file": path.name, "error": str(exc)})
            if not all_rows:
                details = "；".join(f"{item['file']}：{item['error']}" for item in import_errors)
                raise ValueError(f"没有读取到可导入的发货记录。{details}")
            inserted_rows = save_history_rows(HISTORY_DB, all_rows)
            history_rows = load_history_rows(HISTORY_DB)
            payload = _build_payload_from_rows(history_rows, target_date, paths)
            payload["importSummary"] = _build_import_summary(len(all_rows), inserted_rows, import_errors)
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _export_file(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = save_export_file(
                REPORT_DIR,
                payload.get("filename") or "export.txt",
                payload.get("content") or "",
                payload.get("encoding") or "text",
            )
            self._send_json(result)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _history_summary(self, parsed):
        query = parse_qs(parsed.query)
        try:
            target_date = dt.date.fromisoformat(query.get("date", [dt.date.today().isoformat()])[0])
            rows = load_history_rows(HISTORY_DB)
            payload = _build_payload_from_rows(rows, target_date, [HISTORY_DB])
            payload["history"] = {
                "enabled": True,
                "database": str(HISTORY_DB),
                "rows": len(rows),
                "readonly": readonly_mode(),
            }
            self._send_json(payload)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _save_report_package(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            date = payload.get("date") or dt.date.today().isoformat()
            out_dir = REPORT_DIR / date
            out_dir.mkdir(parents=True, exist_ok=True)
            summary_path = out_dir / f"summary-{date}.json"
            detail_path = out_dir / f"details-{date}.csv"
            anomaly_path = out_dir / f"anomalies-{date}.csv"
            summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._write_rows_csv(detail_path, payload.get("rows") or [])
            self._write_rows_csv(anomaly_path, payload.get("anomalies", {}).get("items") or [])
            manifest = {
                "date": date,
                "directory": str(out_dir),
                "summary": str(summary_path),
                "details": str(detail_path),
                "anomalies": str(anomaly_path),
            }
            (out_dir / f"manifest-{date}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send_json(manifest)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)

    def _write_rows_csv(self, path: Path, rows: list[dict]):
        keys = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _send_file(self, path: Path, content_type: str | None = None):
        if not path.exists():
            return self.send_error(404, "Not found")
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict, status: int = 200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _save_uploads(self) -> list[Path]:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            raise ValueError("上传格式不正确。")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        request_dir = Path(tempfile.mkdtemp(prefix="shipments-", dir=UPLOAD_DIR))
        paths = []
        for filename, payload in _iter_uploaded_parts(content_type, body):
            filename = Path(filename).name
            if not filename.lower().endswith(".xlsx"):
                raise ValueError(f"{filename} 不是 .xlsx 文件。")
            target = request_dir / filename
            with target.open("wb") as fh:
                fh.write(payload)
            paths.append(target)
        return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    STATIC_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), ShipmentDashboardHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Shipment dashboard running at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
