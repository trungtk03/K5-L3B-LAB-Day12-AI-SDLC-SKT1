"""File kho cá thể v1.2 (Contract G): {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}.

- Đọc: bắt buộc mảng cá thể hợp lệ; từ chối kho đếm cũ (dict), id trùng, kind lạ, fresh ngoài [0, 100] (BadInput -> mã 2).
- Số học độ tươi: dùng `fractions.Fraction` chính xác tuyệt đối ở ngưỡng 30 và phép floor giá.
- Ghi: sắp theo `id_key`, giữ đủ độ chính xác float khi đọc lại, ghi nguyên tử qua file tạm cùng thư mục.
"""

from fractions import Fraction
import json
import math
import os
import tempfile

from .errors import BadInput
from .ids import id_key, sort_by_id

KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung")
KINDS_P2 = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")
KINDS = KINDS_P2

ITEM_KEYS = {"id", "kind", "fresh"}


def to_fraction(v) -> Fraction:
    if isinstance(v, Fraction):
        return v
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise BadInput(f"fresh phải là số hữu hạn trong [0, 100], đang là {v!r}")
    if isinstance(v, float) and not math.isfinite(v):
        raise BadInput(f"fresh phải là số hữu hạn, đang là {v!r}")
    if isinstance(v, int):
        return Fraction(v)
    return Fraction(v).limit_denominator(1_000_000_000)


def fresh_number(frac: Fraction):
    if frac.denominator == 1:
        return int(frac.numerator)
    return float(frac)


def make_item(item_id: str, kind: str, fresh) -> dict:
    return {"id": item_id, "kind": kind, "fresh_frac": to_fraction(fresh)}


def item_public(it: dict) -> dict:
    if "fresh_frac" in it:
        fval = fresh_number(it["fresh_frac"])
    else:
        fval = it["fresh"]
    return {"id": it["id"], "kind": it["kind"], "fresh": fval}


def validate_item_list(items, field_name="items", kinds=KINDS) -> list:
    """Kiểm tra mảng cá thể {id, kind, fresh} (từ chối dict kho đếm cũ -> mã 2)."""
    if not isinstance(items, list):
        raise BadInput(f"{field_name} phải là mảng cá thể [{{id, kind, fresh}}] theo Contract v1.2")
    out = []
    seen = set()
    for idx, entry in enumerate(items):
        if not isinstance(entry, dict):
            raise BadInput(f"{field_name}[{idx}] phải là object {{id, kind, fresh}}")
        if set(entry.keys()) != ITEM_KEYS:
            raise BadInput(f"{field_name}[{idx}] phải có đúng các khóa id, kind, fresh")
        iid = entry["id"]
        if not isinstance(iid, str) or not iid:
            raise BadInput(f"{field_name}[{idx}].id phải là chuỗi khác rỗng")
        if iid in seen:
            raise BadInput(f"{field_name}: trùng id cá thể {iid!r}")
        seen.add(iid)
        kind = entry["kind"]
        if kind not in kinds:
            raise BadInput(f"{field_name}[{idx}].kind không hợp lệ: {kind!r}")
        ff = to_fraction(entry["fresh"])
        if not (Fraction(0) <= ff <= Fraction(100)):
            raise BadInput(f"{field_name}[{idx}].fresh phải trong [0, 100], đang là {entry['fresh']!r}")
        out.append({"id": iid, "kind": kind, "fresh_frac": ff})
    return out


def read_inventory(path: str, kinds=KINDS) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    parsed = validate_item_list(data["items"], field_name="items", kinds=kinds)
    return sort_by_id(parsed)


def hold_to_items(hold: list) -> list:
    """Giỏ cá thể -> mảng cá thể công khai sắp theo id."""
    return [item_public(it) for it in sort_by_id(hold)]


def write_inventory(path: str, items: list):
    pub = [item_public(it) for it in sorted(items, key=lambda x: id_key(x["id"]))]
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": pub}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
