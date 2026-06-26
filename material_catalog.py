from __future__ import annotations

from pathlib import Path
import re

from summarize_shipments import normalize_header, read_sheet_rows, sheet_paths
import zipfile


PRODUCT_COLUMNS = ["产品名称", "物料名称", "品名", "型号", "型号/品名", "名称", "产品"]
CATEGORY_COLUMNS = ["材料类型", "类型", "分类", "大类", "材料大类", "类别"]
MONTHLY_PRODUCT_COLUMNS = ["产品编码", "产品名称", "产品规格", "新产品名称", "新规格", "原产品名称", "原规格"]
DERIVED_CATEGORY_RULES = [
    ("纯胶", ["纯胶膜", "纯胶"]),
    ("补强", ["补强", "fr-4", "fr4", "钢片"]),
    ("基材", ["基材", "压延铜", "铜箔", "fccl", "单面", "双面"]),
    ("覆盖膜", ["覆盖膜", "保护膜", "cvl"]),
]
KNOWN_MODEL_OVERRIDES = [
    ("OKT-PI2045(F)", "覆盖膜"),
    ("OKT-2045(F)", "覆盖膜"),
]


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


def _normalize_category(category: str) -> str:
    text = str(category or "").strip()
    if "纯胶" in text:
        return "纯胶"
    for name, _keywords in DERIVED_CATEGORY_RULES:
        if name in text:
            return name
    return text or "其他"


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).upper()


def _is_catalog_key(value: str) -> bool:
    text = str(value or "").strip()
    compact = _compact(text)
    if compact.replace(".", "", 1).isdigit():
        return False
    if compact in {"NONE", "NULL", "其他"}:
        return False
    if re.search(r"[\u4e00-\u9fff]", text):
        return len(text) >= 2
    if len(compact) < 4:
        return False
    return True


def _model_family(value: str) -> str:
    compact = _compact(value)
    match = re.search(r"[A-Z]{2,}-[A-Z]+[0-9]{3,}", compact)
    if match:
        return match.group(0)
    short_kts = re.search(r"KTS-([0-9]{3,})", compact)
    if short_kts:
        return f"KTS-PI{short_kts.group(1)}"
    return ""


def derive_material_category(*values: str) -> str:
    text = " ".join(str(value or "") for value in values).lower()
    for name, keywords in DERIVED_CATEGORY_RULES:
        if any(keyword.lower() in text for keyword in keywords):
            return name
    return ""


def _find_catalog_header(rows: list[list[str]]) -> tuple[int, int | None, int | None, list[int]] | None:
    for row_idx, row in enumerate(rows[:30]):
        headers = {normalize_header(value): idx for idx, value in enumerate(row) if normalize_header(value)}
        product_idx = _pick_column(headers, PRODUCT_COLUMNS)
        category_idx = _pick_column(headers, CATEGORY_COLUMNS)
        if product_idx is not None and category_idx is not None:
            return row_idx, product_idx, category_idx, [product_idx]
        monthly_indexes = [
            headers[normalize_header(column)]
            for column in MONTHLY_PRODUCT_COLUMNS
            if normalize_header(column) in headers
        ]
        if len(monthly_indexes) >= 2:
            return row_idx, None, None, monthly_indexes
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
        header_idx, product_idx, category_idx, monthly_indexes = header
        for row in rows[header_idx + 1 :]:
            if category_idx is not None:
                product = _cell(row, product_idx)
                category = _normalize_category(_cell(row, category_idx))
                if _is_catalog_key(product) and category:
                    catalog[product] = category
                continue
            values = [_cell(row, idx) for idx in monthly_indexes]
            category = derive_material_category(*values)
            if not category:
                continue
            for value in values:
                if _is_catalog_key(value):
                    catalog[value] = category
    return catalog


def classify_material(model: str, spec: str, catalog: dict[str, str] | None, rules: list[dict]) -> str:
    text = f"{model or ''} {spec or ''}".lower()
    compact_text = _compact(f"{model or ''} {spec or ''}")
    for token, category in KNOWN_MODEL_OVERRIDES:
        if token in compact_text:
            return category
    catalog_items = sorted(
        (
            (str(product or "").strip(), category)
            for product, category in (catalog or {}).items()
            if _is_catalog_key(str(product or ""))
        ),
        key=lambda item: len(_compact(item[0])),
        reverse=True,
    )
    for product, category in catalog_items:
        product_text = str(product or "").strip().lower()
        if product_text and product_text in text:
            return _normalize_category(category)
    family = _model_family(model)
    if family:
        family_matches = [
            _normalize_category(category)
            for product, category in catalog_items
            if _compact(product).startswith(family)
        ]
        if family_matches:
            return max(set(family_matches), key=family_matches.count)
    derived = derive_material_category(model, spec)
    if derived:
        return derived
    for rule in rules:
        name = _normalize_category(str(rule.get("name") or "").strip())
        keywords = rule.get("keywords") or []
        if name and any(str(keyword).strip().lower() in text for keyword in keywords if str(keyword).strip()):
            return name
    return "其他"
