"""Đọc game.contract.json và kiểm dải hợp lệ của tuning v1.1 (TICKET-02, Test Contract v1.1)."""

import json
import os

from .errors import BadInput

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _range_pair(name, pair, lo, hi):
    if not (isinstance(pair, list) and len(pair) == 2 and all(_num(c) for c in pair) and lo <= pair[0] <= pair[1] <= hi):
        raise BadInput(f"tuning.{name} phải là [min, max] trong [{lo}, {hi}]")


def compute_plan_ingredients(dishes: dict, menu: dict) -> dict:
    totals = {}
    for dish_id, count in dishes.items():
        if dish_id not in menu:
            raise BadInput(f"day_plan: món không tồn tại trong menu: {dish_id!r}")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise BadInput(f"day_plan: số suất của {dish_id} phải là số nguyên dương")
        for ing, qty in menu[dish_id]["recipe"].items():
            totals[ing] = totals.get(ing, 0) + qty * count
    return {k: totals[k] for k in sorted(totals)}


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    validate_tuning(c.get("tuning"))
    return c


def _validate_gather(g):
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")

    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or not {"ca_linh", "ca_loc", "ca_keo"} <= set(fy):
        raise BadInput("tuning.gather.fish_yield phải có đủ ca_linh, ca_loc, ca_keo")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])

    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in ("bong_dien_dien", "bong_sung", "keo_neo"):
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind không hợp lệ")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if not {"bong_dien_dien", "bong_sung", "keo_neo"} <= kinds:
        raise BadInput("tuning.gather.nodes phải có đủ 3 loại rau (bong_dien_dien, bong_sung, keo_neo)")

    # Cá bơi và sinh cá v1.1
    _int_between("gather.fish_initial", g.get("fish_initial"), 1, 30)
    _int_between("gather.fish_max", g.get("fish_max"), g["fish_initial"], 50)
    _between("gather.fish_speed", g.get("fish_speed"), 0.1, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 10_000)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 10_000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 20)
    _range_pair("gather.fish_x", g.get("fish_x"), b["x"][0], b["x"][1])
    for map_name in ("fish_depths", "fish_spawn_depths", "fish_weights"):
        mp = g.get(map_name)
        if not isinstance(mp, dict) or not {"ca_linh", "ca_loc", "ca_keo"} <= set(mp):
            raise BadInput(f"tuning.gather.{map_name} phải có đủ 3 loài cá")
    for k in ("ca_linh", "ca_loc", "ca_keo"):
        _range_pair(f"gather.fish_depths.{k}", g["fish_depths"][k], b["d"][0], b["d"][1])
        if not (isinstance(g["fish_spawn_depths"][k], list) and g["fish_spawn_depths"][k]
                and all(_num(d) and g["fish_depths"][k][0] <= d <= g["fish_depths"][k][1] for d in g["fish_spawn_depths"][k])):
            raise BadInput(f"tuning.gather.fish_spawn_depths.{k} không hợp lệ")
        _between(f"gather.fish_weights.{k}", g["fish_weights"][k], 0.001, 100)
    sx = g.get("fish_spawn_x")
    if not (isinstance(sx, list) and sx and all(_num(x) and g["fish_x"][0] <= x <= g["fish_x"][1] for x in sx)):
        raise BadInput("tuning.gather.fish_spawn_x không hợp lệ")

    # Thủy quái (Cá Sấu Năm Chèo)
    ms = g.get("monsters")
    if not isinstance(ms, dict):
        raise BadInput("tuning.gather.monsters phải là object")
    _int_between("gather.monsters.invuln_ticks", ms.get("invuln_ticks"), 0, 10_000)
    _between("gather.monsters.loss_ratio", ms.get("loss_ratio"), 0, 1)
    species = ms.get("species")
    if not isinstance(species, dict) or "ca_sau" not in species:
        raise BadInput("tuning.gather.monsters.species phải có 'ca_sau'")
    for sk, sp in species.items():
        if not isinstance(sp, dict):
            raise BadInput(f"tuning.gather.monsters.species.{sk} phải là object")
        _between(f"monsters.{sk}.patrol_speed", sp.get("patrol_speed"), 0.1, 20)
        _between(f"monsters.{sk}.chase_speed", sp.get("chase_speed"), 0.1, 20)
        _between(f"monsters.{sk}.detect_radius", sp.get("detect_radius"), 0.5, 50)
        _between(f"monsters.{sk}.exit_radius", sp.get("exit_radius"), sp["detect_radius"], 100)
        _range_pair(f"monsters.{sk}.depths", sp.get("depths"), b["d"][0], b["d"][1])
        _between(f"monsters.{sk}.hit_radius", sp.get("hit_radius"), 0.1, 10)
        _int_between(f"monsters.{sk}.recoil_ticks", sp.get("recoil_ticks"), 1, 1000)
        _between(f"monsters.{sk}.recoil_dist", sp.get("recoil_dist"), 0, 20)
    spawns = ms.get("spawns")
    if not isinstance(spawns, list) or not spawns:
        raise BadInput("tuning.gather.monsters.spawns phải là mảng không rỗng")
    seen_m = set()
    for m in spawns:
        if not isinstance(m, dict) or not isinstance(m.get("id"), str) or m["id"] in seen_m:
            raise BadInput("tuning.gather.monsters.spawns: mỗi con cần id duy nhất")
        seen_m.add(m["id"])
        if m.get("kind") not in species:
            raise BadInput(f"tuning.gather.monsters.spawns.{m['id']}: kind không tồn tại")
        _pos_in(f"monsters.{m['id']}.pos", m.get("pos"), b, ("x", "d"))
        wps = m.get("waypoints")
        if not isinstance(wps, list) or len(wps) != 2:
            raise BadInput(f"tuning.gather.monsters.spawns.{m['id']}.waypoints phải có đúng 2 điểm")
        for i, wp in enumerate(wps):
            _pos_in(f"monsters.{m['id']}.waypoints[{i}]", wp, b, ("x", "d"))
        _int_between(f"monsters.{m['id']}.from_day", m.get("from_day", 1), 1, 5)


def validate_tuning(t):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    _validate_gather(g)

    # Quán v1.1
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, int(q["duration_s"] * 60) - 1)
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null trong lõi")

    for dish_id, d in menu.items():
        price, cook = d.get("price"), d.get("cook_s")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or not _num(cook) or cook <= 0:
            raise BadInput(f"menu.{dish_id}: price (nguyên) và cook_s phải > 0")

    # Kế hoạch Ngày (day_plan D1..D5)
    dp = t.get("day_plan")
    if not isinstance(dp, list) or len(dp) != 5:
        raise BadInput("tuning.day_plan phải là mảng đúng 5 Ngày (D1..D5)")
    seen_days = set()
    for entry in dp:
        if not isinstance(entry, dict):
            raise BadInput("tuning.day_plan: mỗi phần tử phải là object")
        dnum = entry.get("day")
        _int_between("day_plan.day", dnum, 1, 5)
        if dnum in seen_days:
            raise BadInput(f"tuning.day_plan: trùng ngày {dnum}")
        seen_days.add(dnum)
        dishes = entry.get("dishes")
        if not isinstance(dishes, dict) or not dishes:
            raise BadInput(f"tuning.day_plan[day={dnum}].dishes phải là object không rỗng")
        calc = compute_plan_ingredients(dishes, menu)
        if entry.get("ingredients") != calc:
            raise BadInput(f"tuning.day_plan[day={dnum}].ingredients không khớp tổng công thức ({calc})")

    # Shop v1.1
    shop = t.get("shop")
    if not isinstance(shop, dict):
        raise BadInput("tuning.shop phải là object")
    _int_between("shop.max_ticks", shop.get("max_ticks"), 1, 100_000)
    up = shop.get("upgrades")
    if not isinstance(up, dict) or not {"oxygen", "hp"} <= set(up):
        raise BadInput("tuning.shop.upgrades phải có 'oxygen' và 'hp'")
    for uid, key in (("oxygen", "oxygen_max_s"), ("hp", "hp_max")):
        tiers = up[uid]
        if not isinstance(tiers, list) or not tiers:
            raise BadInput(f"tuning.shop.upgrades.{uid} phải là mảng không rỗng")
        for idx, tier in enumerate(tiers, 1):
            if not isinstance(tier, dict) or tier.get("level") != idx:
                raise BadInput(f"tuning.shop.upgrades.{uid}: level phải tăng liên tiếp từ 1")
            _int_between(f"shop.upgrades.{uid}[{idx}].price", tier.get("price"), 1, 1_000_000)
            if not _num(tier.get(key)) or tier[key] <= 0:
                raise BadInput(f"tuning.shop.upgrades.{uid}[{idx}].{key} phải > 0")

    # Độ tươi v1.2
    fr = t.get("freshness")
    if not isinstance(fr, dict):
        raise BadInput("tuning.freshness phải là object")
    _between("freshness.initial", fr.get("initial"), 1, 100)
    _between("freshness.gather_decay_per_s", fr.get("gather_decay_per_s"), 0, 100)
    _between("freshness.quan_decay_per_s", fr.get("quan_decay_per_s"), 0, 100)
    _between("freshness.spoiled_below", fr.get("spoiled_below"), 0, fr["initial"])
