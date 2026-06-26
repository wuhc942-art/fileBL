from __future__ import annotations

from pathlib import Path

from summarize_shipments import normalize_header, read_sheet_rows, sheet_paths
import zipfile


PRODUCT_COLUMNS = ["产品名称", "物料名称", "品名", "型号", "型号/品名", "名称", "产品"]
CATEGORY_COLUMNS = ["材料类型", "类型", "分类", "大类", "材料大类", "类别"]


def _pick_column(headers: dict[str, int], candidates: list[str]) -> int | None:
    for candidate in candidates:
        idx = headers.get(normalize_header(candidate))
        if idx is not None:
            return idx
    return None


def _cell(row: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    return str(row[idx] or "").strip()


def _find_catalog_header(rows: list[list[str]]) -> tuple[int, int, int] | None:
    for row_idx, row in enumerate(rows[:30]):
        headers = {normalize_header(value): idx for idx, value in enumerate(row) if normalize_header(value)}
        product_idx = _pick_column(headers, PRODUCT_COLUMNS)
        category_idx = _pick_column(headers, CATEGORY_COLUMNS)
        if product_idx is not None and category_idx is not None:
            return row_idx, product_idx, category_idx
    return None


def _sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return list(sheet_paths(zf).keys())


def load_material_catalog(path: Path | str) -> dict[str, str]:
    workbook = Path(path)
    catalog: dict[str, str] = {}
    for sheet_name in _sheet_names(workbook):
        try:
            rows = read_sheet_rows(workbook, sheet_name)
        except Exception:
            continue
        header = _find_catalog_header(rows)
        if header is None:
            continue
        header_idx, product_idx, category_idx = header
        for row in rows[header_idx + 1 :]:
            product = _cell(row, product_idx)
            category = _cell(row, category_idx)
            if product and category:
                catalog[product] = category
    return catalog


def classify_material(model: str, spec: str, catalog: dict[str, str] | None, rules: list[dict]) -> str:
    text = f"{model or ''} {spec or ''}".lower()
    for product, category in (catalog or {}).items():
        product_text = str(product or "").strip().lower()
        if product_text and product_text in text:
            return str(category or "").strip() or "其他"
    for rule in rules:
        name = str(rule.get("name") or "").strip()
        keywords = rule.get("keywords") or []
        if name and any(str(keyword).strip().lower() in text for keyword in keywords if str(keyword).strip()):
            return name
    return "其他"
