"""Nạp và kiểm scenario (Contract D v1.1).

- Với gather / quan: trả về dict khối tương ứng.
- Với day: trả về dict {"day": ..., "gather": ..., "quan": ...}.
Mọi mâu thuẫn cú pháp / miền giá trị / mức luật -> BadInput (mã thoát 2 trước khi ghi đầu ra).
"""

import json
import math

from .contract import compute_plan_ingredients
from .errors import BadInput
from .inventory import KINDS, validate_item_list

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "monsters", "time_left_ticks"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}
DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}


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
            raise BadInput(f"{name} nằm ngoài vùng ({axis} ∈ [{lo}, {hi}])")


def _effective_gather_caps(tuning, upgrades=None):
    g = tuning["gather"]
    oxy_s = g["oxygen_max_s"]
    hp_max = g["hp_max"]
    if upgrades:
        shop_up = tuning["shop"]["upgrades"]
        olvl = upgrades.get("oxygen", 0)
        if olvl > 0:
            oxy_s = next(t["oxygen_max_s"] for t in shop_up["oxygen"] if t["level"] == olvl)
        hlvl = upgrades.get("hp", 0)
        if hlvl > 0:
            hp_max = next(t["hp_max"] for t in shop_up["hp"] if t["level"] == hlvl)
    return int(round(oxy_s * 60)), int(hp_max)


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return {} if mode != "day" else {"day": {}, "gather": {}, "quan": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if not isinstance(data, dict):
        raise BadInput("scenario phải là JSON object")

    if mode == "day":
        allowed_top = {"day", "gather", "quan"}
        extra_top = set(data) - allowed_top
        if extra_top:
            raise BadInput(f"chạy --mode day chỉ nhận các khối day/gather/quan, gặp: {sorted(extra_top)}")
        day_blk = data.get("day", {})
        gather_blk = data.get("gather", {})
        quan_blk = data.get("quan", {})
        for k, blk in (("day", day_blk), ("gather", gather_blk), ("quan", quan_blk)):
            if not isinstance(blk, dict):
                raise BadInput(f"khối {k} phải là object")
        _validate_day(day_blk, tuning)
        upgrades = day_blk.get("upgrades", {})
        _validate_gather_block(gather_blk, tuning, upgrades=upgrades)
        _validate_quan_block(quan_blk, tuning, in_day=True)
        return {"day": day_blk, "gather": gather_blk, "quan": quan_blk}

    if not set(data) <= {"gather", "quan"}:
        raise BadInput("scenario chỉ được có khối 'gather' hoặc 'quan'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    if mode == "gather":
        _validate_gather_block(block, tuning)
    else:
        _validate_quan_block(block, tuning, in_day=False)
    return block


def _validate_day(b, tuning):
    extra = set(b) - DAY_KEYS
    if extra:
        raise BadInput(f"trường lạ trong day: {sorted(extra)}")
    has_money = "money" in b
    has_earned = "earned" in b
    if has_money:
        _nonneg_int("day.money", b["money"])
    if has_earned:
        _nonneg_int("day.earned", b["earned"])
    money = b.get("money", 0)
    earned = b.get("earned", 0)
    if money > 0 and not (has_money and has_earned):
        raise BadInput("day: cần khai cả money và earned khi có tiền đầu kỳ")
    if money > earned:
        raise BadInput(f"day: money ({money}) không được lớn hơn earned ({earned})")
    q = tuning["quan"]
    if "reputation" in b:
        rep = b["reputation"]
        if not _num(rep) or not (q["reputation_min"] <= rep <= q["reputation_max"]):
            raise BadInput(f"day.reputation phải trong [{q['reputation_min']}, {q['reputation_max']}]")
    if "upgrades" in b:
        up = b["upgrades"]
        if not isinstance(up, dict):
            raise BadInput("day.upgrades phải là object")
        shop_up = tuning["shop"]["upgrades"]
        for k, v in up.items():
            if k not in shop_up:
                raise BadInput(f"day.upgrades: nâng cấp không hợp lệ: {k!r}")
            _nonneg_int(f"day.upgrades.{k}", v)
            max_lvl = max(t["level"] for t in shop_up[k])
            if v > max_lvl:
                raise BadInput(f"day.upgrades.{k} ({v}) vượt cấp tối đa ({max_lvl})")
    if "day_plan" in b:
        dp = b["day_plan"]
        if not isinstance(dp, list):
            raise BadInput("day.day_plan phải là mảng")
        seen = set()
        for entry in dp:
            if not isinstance(entry, dict):
                raise BadInput("day.day_plan: mỗi phần tử phải là object")
            dnum = entry.get("day")
            if isinstance(dnum, bool) or not isinstance(dnum, int) or not (1 <= dnum <= 5):
                raise BadInput(f"day.day_plan: day phải là số nguyên trong [1, 5], đang là {dnum!r}")
            if dnum in seen:
                raise BadInput(f"day.day_plan: trùng ngày {dnum}")
            seen.add(dnum)
            dishes = entry.get("dishes")
            if not isinstance(dishes, dict) or not dishes:
                raise BadInput(f"day.day_plan[day={dnum}]: dishes phải là object không rỗng")
            calc = compute_plan_ingredients(dishes, tuning["menu"])
            if "ingredients" in entry and entry["ingredients"] != calc:
                raise BadInput(f"day.day_plan[day={dnum}]: ingredients không khớp tổng công thức ({calc})")


def _validate_gather_block(b, tuning, upgrades=None):
    extra = set(b) - GATHER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather: {sorted(extra)}")
    dur = int(round(tuning["gather"]["duration_s"] * 60))
    if "time_left_ticks" in b:
        t = b["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish", "monsters"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = validate_item_list(b["hold"], field_name="gather.hold")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra_p = set(p) - GATHER_PLAYER_KEYS
    if extra_p:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra_p)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax, hp_max = _effective_gather_caps(tuning, upgrades)
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= hp_max):
        raise BadInput(f"player.hp phải trong [1, {hp_max}]")
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
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])

    species = g["monsters"]["species"]
    for m in b.get("monsters", []):
        kind = m.get("kind")
        if kind not in species:
            raise BadInput(f"monsters.{m['id']}: kind không hợp lệ: {kind!r}")
        sp = species[kind]
        d_lo, d_hi = sp["depths"]
        _pos(f"monsters.{m['id']}.pos", m.get("pos"), bounds)
        if not (d_lo <= m["pos"][1] <= d_hi):
            raise BadInput(f"monsters.{m['id']}.pos nằm ngoài dải độ sâu [{d_lo}, {d_hi}]")
        wps = m.get("waypoints")
        if not isinstance(wps, list) or len(wps) != 2:
            raise BadInput(f"monsters.{m['id']}.waypoints phải có đúng 2 điểm")
        for idx, wp in enumerate(wps):
            _pos(f"monsters.{m['id']}.waypoints[{idx}]", wp, bounds)
            if not (d_lo <= wp[1] <= d_hi):
                raise BadInput(f"monsters.{m['id']}.waypoints[{idx}] nằm ngoài dải độ sâu [{d_lo}, {d_hi}]")
        if "target_idx" in m:
            tidx = m["target_idx"]
            if isinstance(tidx, bool) or tidx not in (0, 1):
                raise BadInput(f"monsters.{m['id']}.target_idx phải là 0 hoặc 1")
        st = m.get("state", "patrol")
        if st not in ("patrol", "chase", "recoil"):
            raise BadInput(f"monsters.{m['id']}.state không hợp lệ: {st!r}")
        stl = m.get("state_ticks_left", 0)
        _nonneg_int(f"monsters.{m['id']}.state_ticks_left", stl)
        rdir = m.get("recoil_dir")
        if st == "recoil":
            if stl <= 0:
                raise BadInput(f"monsters.{m['id']}: trạng thái recoil cần state_ticks_left > 0")
            if not (isinstance(rdir, list) and len(rdir) == 2 and all(_num(c) for c in rdir)):
                raise BadInput(f"monsters.{m['id']}: recoil cần recoil_dir là vector đơn vị [dx, dd]")
            mag = math.hypot(rdir[0], rdir[1])
            if abs(mag - 1.0) > 1e-2:
                raise BadInput(f"monsters.{m['id']}: recoil_dir phải là vector đơn vị")
        else:
            if stl != 0:
                raise BadInput(f"monsters.{m['id']}: trạng thái {st} phải có state_ticks_left == 0")
            if rdir is not None:
                raise BadInput(f"monsters.{m['id']}: trạng thái {st} phải có recoil_dir == null")


def _validate_quan_block(b, tuning, in_day=False):
    extra = set(b) - QUAN_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong quan: {sorted(extra)}")
    if in_day:
        if "stock" in b:
            raise BadInput("cấm dùng quan.stock khi chạy --mode day (hãy dùng gather.hold)")
        if "reputation" in b:
            raise BadInput("cấm dùng quan.reputation khi chạy --mode day (hãy dùng day.reputation)")
    dur = int(round(tuning["quan"]["duration_s"] * 60))
    if "time_left_ticks" in b:
        t = b["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
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
        validate_item_list(b["stock"], field_name="quan.stock")
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
            if os_val not in ("reserved", "assigned", "served", "unfulfillable"):
                raise BadInput(f"customers.{c['id']}: order_status không hợp lệ: {os_val!r}")
            if st == "eating" and os_val != "served":
                raise BadInput(f"customers.{c['id']}: khách eating phải có order_status='served'")
            if st == "waiting" and os_val == "served":
                raise BadInput(f"customers.{c['id']}: khách waiting không thể có order_status='served'")
        for tk in ("order_tick", "patience_ticks_left", "eat_ticks_left"):
            if tk in c:
                _nonneg_int(f"customers.{c['id']}.{tk}", c[tk])
        if "reserved" in c:
            res = c["reserved"]
            if not isinstance(res, list) or any(not isinstance(rid, str) or not rid for rid in res):
                raise BadInput(f"customers.{c['id']}.reserved phải là mảng id cá thể (chuỗi khác rỗng)")
            if len(res) != len(set(res)):
                raise BadInput(f"customers.{c['id']}.reserved có id trùng lặp")
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
