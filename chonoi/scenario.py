"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
TODO(nhóm): bổ sung kiểm mâu thuẫn mức luật mà nhóm cần (khách giữ chỗ quá kho, đơn assigned
phải có đúng một món, khách eating thiếu giá/tip...) — xem PRD-0 mục D và 'Mâu thuẫn -> mã 2'.
"""

import json

from .errors import BadInput
from .inventory import KINDS_P1, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung")
FISH_KINDS = ("ca_linh", "ca_loc")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan"}:
        raise BadInput("scenario chỉ được có khối 'gather' hoặc 'quan'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)
    return block


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(k not in KINDS_P1 for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round(g["oxygen_max_s"] * 60))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")


def _validate_quan(b, tuning):
    q = tuning["quan"]
    menu = tuning["menu"]
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    if "reputation" in b:
        rep = b["reputation"]
        if not _num(rep) or not (q["reputation_min"] <= rep <= q["reputation_max"]):
            raise BadInput(f"quan.reputation phải trong [{q['reputation_min']}, {q['reputation_max']}]")
    if "stock" in b:
        validate_items(b["stock"])
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = q["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    if "hand" in b and b["hand"] is not None:
        h = b["hand"]
        if not isinstance(h, dict):
            raise BadInput("quan.hand phải là object hoặc null")
        if not isinstance(h.get("order_id"), str) or not h["order_id"]:
            raise BadInput("quan.hand.order_id phải là chuỗi khác rỗng")
        if h.get("dish_id") not in menu:
            raise BadInput(f"quan.hand.dish_id không có trong menu: {h.get('dish_id')!r}")
        if "base_price" in h and (isinstance(h["base_price"], bool) or not isinstance(h["base_price"], int) or h["base_price"] <= 0):
            raise BadInput("quan.hand.base_price phải là số nguyên dương")
    for s in b.get("stoves", []):
        if "pos" in s:
            _pos(f"stoves.{s['id']}.pos", s["pos"], qb, axes=("x", "z"))
        st = s.get("state", "idle")
        if st not in ("idle", "cooking", "ready"):
            raise BadInput(f"stoves.{s['id']}: state không hợp lệ: {st!r}")
        dish = s.get("dish")
        if dish is not None and dish not in menu:
            raise BadInput(f"stoves.{s['id']}: dish không có trong menu: {dish!r}")
        if "cook_ticks_left" in s:
            _nonneg_int(f"stoves.{s['id']}.cook_ticks_left", s["cook_ticks_left"])
        if "ready_ticks" in s:
            _nonneg_int(f"stoves.{s['id']}.ready_ticks", s["ready_ticks"])
        if "base_price" in s and s["base_price"] is not None:
            bp = s["base_price"]
            if isinstance(bp, bool) or not isinstance(bp, int) or bp <= 0:
                raise BadInput(f"stoves.{s['id']}.base_price phải là số nguyên dương")
        if st == "idle":
            if dish is not None or s.get("cook_ticks_left", 0) != 0 or s.get("ready_ticks", 0) != 0:
                raise BadInput(f"stoves.{s['id']}: bếp idle không được có dish hoặc bộ đếm > 0")
        elif st == "cooking":
            if dish is None or s.get("cook_ticks_left", 0) <= 0:
                raise BadInput(f"stoves.{s['id']}: bếp cooking cần dish hợp lệ và cook_ticks_left >= 1")
            if not isinstance(s.get("order_id"), str) or not s["order_id"]:
                raise BadInput(f"stoves.{s['id']}: bếp cooking cần order_id")
        elif st == "ready":
            if dish is None or s.get("cook_ticks_left", 0) != 0:
                raise BadInput(f"stoves.{s['id']}: bếp ready cần dish hợp lệ và cook_ticks_left == 0")
            if not isinstance(s.get("order_id"), str) or not s["order_id"]:
                raise BadInput(f"stoves.{s['id']}: bếp ready cần order_id")
    for tb in b.get("tables", []):
        if "pos" in tb:
            _pos(f"tables.{tb['id']}.pos", tb["pos"], qb, axes=("x", "z"))
    table_ids = [c.get("table_id") for c in b.get("customers", [])]
    known = {t["id"] for t in q["tables"]} | {t.get("id") for t in b.get("tables", [])}
    for c in b.get("customers", []):
        if not isinstance(c.get("table_id"), str) or c["table_id"] not in known:
            raise BadInput(f"customers.{c['id']}: table_id phải là bàn có thật")
        if c.get("dish_id") not in menu:
            raise BadInput(f"customers.{c['id']}: dish_id không có trong menu: {c.get('dish_id')!r}")
        st = c.get("state", "waiting")
        if st not in ("waiting", "eating"):
            raise BadInput(f"customers.{c['id']}: state không hợp lệ: {st!r}")
        if "order_status" in c:
            os_val = c["order_status"]
            if os_val not in ("reserved", "assigned", "served"):
                raise BadInput(f"customers.{c['id']}: order_status không hợp lệ: {os_val!r}")
            if st == "eating" and os_val != "served":
                raise BadInput(f"customers.{c['id']}: khách eating phải có order_status='served'")
            if st == "waiting" and os_val == "served":
                raise BadInput(f"customers.{c['id']}: khách waiting không thể có order_status='served'")
        for tk in ("order_tick", "patience_ticks_left", "eat_ticks_left"):
            if tk in c:
                _nonneg_int(f"customers.{c['id']}.{tk}", c[tk])
        if "reserved" in c:
            validate_items(c["reserved"])
        if st == "eating":
            bp, tip = c.get("base_price"), c.get("tip")
            if isinstance(bp, bool) or not isinstance(bp, int) or bp <= 0:
                raise BadInput(f"customers.{c['id']}: khách eating phải có base_price (nguyên > 0)")
            if isinstance(tip, bool) or not isinstance(tip, int) or tip < 0:
                raise BadInput(f"customers.{c['id']}: khách eating phải có tip (nguyên >= 0)")
            if c.get("reserved"):
                raise BadInput(f"customers.{c['id']}: khách eating không được còn giữ chỗ nguyên liệu")
        else:
            if "base_price" in c and c["base_price"] is not None:
                bp = c["base_price"]
                if isinstance(bp, bool) or not isinstance(bp, int) or bp <= 0:
                    raise BadInput(f"customers.{c['id']}.base_price phải là số nguyên dương")
            if "tip" in c and c["tip"] is not None:
                tip = c["tip"]
                if isinstance(tip, bool) or not isinstance(tip, int) or tip < 0:
                    raise BadInput(f"customers.{c['id']}.tip phải là số nguyên không âm")
    if len(table_ids) != len(set(table_ids)):
        raise BadInput("hai khách cùng bàn")
