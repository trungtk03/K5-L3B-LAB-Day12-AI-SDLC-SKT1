"""Buổi sáng — Lặn & Hái (`gather`, Contract v1.2).

Hoàn thiện đầy đủ Phase 1 + Phase 2 + Phase 3 (Độ tươi & kho cá thể):
  - Kho giỏ là mảng cá thể `{id, kind, fresh}` (LIFO theo thứ tự nhặt), cấp id `I1, I2, ...` tăng xuyên pha/Ngày.
  - Hao tươi đầu bước: `-0.5/s` (`-1/120` mỗi tick, dùng `Fraction` chính xác), kẹp đáy 0; hàng mới `fresh=100` hao từ bước sau.
  - Ngưỡng ươn `< 30` (so trước làm tròn): phát `spoiled` đúng 1 lần theo thứ tự `id`.
  - 6 nút hái (`N1–N6`), 3 loài cá (`ca_linh`, `ca_loc`, `ca_keo`), 8 đàn đầu ca, cá bơi `1.5 m/s` phản xạ mép/góc + sinh cá `360·k`.
  - Cá Sấu Năm Chèo (`M1`/`M2`): `patrol`/`chase`/`recoil`, chạm mất 1 Máu + rơi `floor(n/2)` cá thể theo LIFO + `invuln_ticks=90`, ngất (`faint`).
"""

from fractions import Fraction
import math

from ..ids import id_key, sort_by_id
from ..inventory import hold_to_items, item_public, make_item, to_fraction
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


def _resolve_upgrades(tuning, active_upgrades):
    g = tuning["gather"]
    oxy_s = g["oxygen_max_s"]
    hp_max = g["hp_max"]
    if active_upgrades:
        shop_up = tuning["shop"]["upgrades"]
        olvl = active_upgrades.get("oxygen", 0)
        if olvl > 0:
            for tier in shop_up["oxygen"]:
                if tier["level"] == olvl:
                    oxy_s = tier["oxygen_max_s"]
                    break
        hlvl = active_upgrades.get("hp", 0)
        if hlvl > 0:
            for tier in shop_up["hp"]:
                if tier["level"] == hlvl:
                    hp_max = tier["hp_max"]
                    break
    return oxy_s, int(hp_max)


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1, active_upgrades=None,
                 money=0, earned=0, reputation=None, item_ids=None, reallocate_hold_ids=False):
        t = tuning["gather"]
        fr = tuning["freshness"]
        self.t = t
        self.tuning = tuning
        self.rng = streams
        self.ids = ids
        self.item_ids = item_ids if item_ids is not None else ids
        self.day = int(day)

        self.fresh_initial = to_fraction(fr["initial"])
        self.fresh_decay = to_fraction(fr["gather_decay_per_s"]) / Fraction(60)
        self.spoiled_below = to_fraction(fr["spoiled_below"])

        oxy_s, hp_max = _resolve_upgrades(tuning, active_upgrades)
        self.oxygen_max = int(round(oxy_s * TICK))
        self.hp_max = hp_max

        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)

        # Giỏ cá thể {id, kind, fresh_frac} theo thứ tự nhặt (cuối mảng là mới nhất - LIFO)
        self.hold = []
        for raw_it in scenario.get("hold", []):
            if reallocate_hold_ids:
                iid = self.item_ids.new("I")
            else:
                iid = raw_it["id"]
                self.item_ids.reserve(iid)
            self.hold.append(make_item(iid, raw_it["kind"], raw_it["fresh"]))

        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = 0
        self.random_fish = scenario.get("random_fish", True)

        # Nút hái mặt nước
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [
            {
                "id": n["id"],
                "kind": n["kind"],
                "pos": [float(c) for c in n["pos"]],
                "regrow_ticks": n.get("regrow_ticks", 0),
            }
            for n in src_nodes
        ]
        for n in self.nodes:
            ids.reserve(n["id"])

        # Đàn cá
        self.fish = []
        if "fish" in scenario:
            for f in scenario["fish"]:
                self.fish.append({
                    "id": f["id"],
                    "kind": f["kind"],
                    "pos": [float(c) for c in f["pos"]],
                    "heading_deg": float(f.get("heading_deg", 0.0)),
                    "age_ticks": int(f.get("age_ticks", 0)),
                })
                ids.reserve(f["id"])
        elif self.random_fish:
            if isinstance(t["fish_initial"], list):
                for f in t["fish_initial"]:
                    self.fish.append({
                        "id": f["id"],
                        "kind": f["kind"],
                        "pos": [float(c) for c in f["pos"]],
                        "heading_deg": float(f.get("heading_deg", 0.0)),
                        "age_ticks": int(f.get("age_ticks", 0)),
                    })
                    ids.reserve(f["id"])
            else:
                self._spawn_initial_fish(int(t["fish_initial"]))

        # Thủy quái (Cá Sấu Năm Chèo)
        self.monster_cfg = t["monsters"]
        self.monsters = []
        if "monsters" in scenario:
            for m in scenario["monsters"]:
                self.monsters.append({
                    "id": m["id"],
                    "kind": m["kind"],
                    "pos": [float(c) for c in m["pos"]],
                    "waypoints": [[float(c) for c in wp] for wp in m["waypoints"]],
                    "target_idx": int(m.get("target_idx", 1)),
                    "state": m.get("state", "patrol"),
                    "state_ticks_left": int(m.get("state_ticks_left", 0)),
                    "recoil_dir": [float(c) for c in m["recoil_dir"]] if m.get("recoil_dir") is not None else None,
                })
                ids.reserve(m["id"])
        else:
            for sp in self.monster_cfg.get("spawns", []):
                if int(sp.get("from_day", 1)) <= self.day:
                    self.monsters.append({
                        "id": sp["id"],
                        "kind": sp["kind"],
                        "pos": [float(c) for c in sp["pos"]],
                        "waypoints": [[float(c) for c in wp] for wp in sp["waypoints"]],
                        "target_idx": 1,
                        "state": "patrol",
                        "state_ticks_left": 0,
                        "recoil_dir": None,
                    })
                    ids.reserve(sp["id"])

        self.money = int(money)
        self.earned = int(earned)
        self.reputation = float(tuning["quan"]["reputation_initial"] if reputation is None else reputation)
        self.done = False
        self.reason = None

    # --- giao diện cho runner / day -------------------------------------------
    def inventory_items(self) -> list:
        """Mảng cá thể công khai sắp theo id (dùng cho gather_end & ghi file kho)."""
        return hold_to_items(self.hold)

    def inventory_internal(self) -> list:
        """Bản sao cá thể giữ nguyên Fraction chính xác để bàn giao trong bộ nhớ cho day."""
        return [dict(it) for it in sort_by_id(self.hold)]

    def snapshot(self) -> dict:
        return {
            "player": {
                "pos": list(self.pos),
                "vel": list(self.vel),
                "heading_deg": self.heading,
                "oxygen_ticks": self.oxygen_ticks,
                "oxygen_max_ticks": self.oxygen_max,
                "hp": self.hp,
                "hp_max": self.hp_max,
                "zero_oxy_ticks": self.zero_oxy_ticks,
                "invuln_ticks": self.invuln_ticks,
                "catch_cd_ticks": self.catch_cd_ticks,
                "at_surface": self._at_surface(),
            },
            "hold": [item_public(it) for it in self.hold],
            "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [
                {
                    "id": n["id"],
                    "pos": list(n["pos"]),
                    "kind": n["kind"],
                    "ready": n["regrow_ticks"] == 0,
                    "regrow_ticks": n["regrow_ticks"],
                }
                for n in sort_by_id(self.nodes)
            ],
            "fish": [
                {
                    "id": f["id"],
                    "pos": list(f["pos"]),
                    "kind": f["kind"],
                    "heading_deg": f["heading_deg"],
                    "age_ticks": f["age_ticks"],
                }
                for f in sort_by_id(self.fish)
            ],
            "monsters": [
                {
                    "id": m["id"],
                    "kind": m["kind"],
                    "pos": list(m["pos"]),
                    "state": m["state"],
                    "state_ticks_left": m["state_ticks_left"],
                    "target_idx": m["target_idx"],
                    "waypoints": [list(wp) for wp in m["waypoints"]],
                    "recoil_dir": list(m["recoil_dir"]) if m["recoil_dir"] is not None else None,
                }
                for m in sort_by_id(self.monsters)
            ],
        }

    # --- một bước (đúng thứ tự Contract v1.2 mục 1) ---------------------------
    def step(self, inp):
        events = []

        # 1. Đồng hồ, cooldown, giảm bất tử, hồi nút và hao tươi hàng sẵn có đầu bước
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))

        newly_spoiled = []
        for it in self.hold:
            prev = it["fresh_frac"]
            now = max(Fraction(0), prev - self.fresh_decay)
            it["fresh_frac"] = now
            if prev >= self.spoiled_below and now < self.spoiled_below:
                newly_spoiled.append(it)
        for it in sort_by_id(newly_spoiled):
            events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": "hold"}))

        # 2. Bơi, oxy, ngạt
        was_surface = self._at_surface()
        self._move(inp)
        now_surface = self._at_surface()
        if was_surface and not now_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif not was_surface and now_surface:
            events.append(("surface", {"pos": list(self.pos)}))

        if now_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"])
            self.zero_oxy_ticks = 0
        else:
            prev_oxy = self.oxygen_ticks
            self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
            if prev_oxy > 0 and self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"oxygen_ticks": 0}))

            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= self.t["choke_interval_ticks"]:
                    self.zero_oxy_ticks = 0
                    self.hp -= 1
                    events.append(("choke", {"hp": max(0, self.hp)}))
                    if self.hp <= 0:
                        self.hp = 0
                        lost_items = [item_public(it) for it in reversed(self.hold)]
                        self.hold = []
                        events.append(("faint", {"cause": "choke", "lost": lost_items, "hp": 0}))
                        self._finish("fainted", events)
                        return events

        # 3. Cập nhật quái theo id rồi xét tối đa một hit
        if self._step_monsters(events):
            return events

        # 4. Tương tác: bến trước, rồi hái nút mặt nước
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if self._at_surface():
                rad = self.t["interact_radius"]
                candidates = []
                for n in self.nodes:
                    if n["regrow_ticks"] == 0:
                        d = math.dist(self.pos, n["pos"])
                        if d <= rad:
                            candidates.append((d, id_key(n["id"]), n))
                if candidates:
                    candidates.sort(key=lambda item: (item[0], item[1]))
                    best_node = candidates[0][2]
                    req = self.t["node_yield"]
                    free = self.t["hold_capacity"] - len(self.hold)
                    if len(self.hold) + req <= self.t["hold_capacity"]:
                        for _ in range(req):
                            self.hold.append(make_item(self.item_ids.new("I"), best_node["kind"], self.fresh_initial))
                        best_node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
                        events.append(("gather", {"node_id": best_node["id"], "kind": best_node["kind"], "amount": req}))
                    else:
                        events.append(("hold_full", {"action": "gather", "node_id": best_node["id"],
                                                     "required": req, "free": free}))

        # 5. Bắt cá (theo vị trí cá TRƯỚC khi cá bơi)
        if inp.pressed("catch"):
            if self.catch_cd_ticks == 0 and not self._at_surface():
                rad = self.t["catch_radius"]
                candidates = []
                for f in self.fish:
                    d = math.dist(self.pos, f["pos"])
                    if d <= rad:
                        candidates.append((d, id_key(f["id"]), f))
                if candidates:
                    candidates.sort(key=lambda item: (item[0], item[1]))
                    best_fish = candidates[0][2]
                    yield_count = self.t["fish_yield"][best_fish["kind"]]
                    free = self.t["hold_capacity"] - len(self.hold)
                    if len(self.hold) + yield_count <= self.t["hold_capacity"]:
                        for _ in range(yield_count):
                            self.hold.append(make_item(self.item_ids.new("I"), best_fish["kind"], self.fresh_initial))
                        self.fish.remove(best_fish)
                        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
                        events.append(("fish_caught", {"fish_id": best_fish["id"], "kind": best_fish["kind"],
                                                       "yield": yield_count}))
                    else:
                        events.append(("hold_full", {"action": "catch", "fish_id": best_fish["id"],
                                                     "required": yield_count, "free": free}))

        # 6. Xét hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events

        # 7. Nếu còn giờ và bật random_fish: cá bơi, rồi sinh thêm theo lịch
        if self.random_fish:
            self._step_fish_swim()
            self._maybe_spawn_fish(events)

        return events

    # --- Cá Sấu Năm Chèo -------------------------------------------------------
    def _clamp_monster(self, pos, sp):
        b = self.t["bounds"]
        d_lo, d_hi = sp["depths"]
        pos[0] = min(float(b["x"][1]), max(float(b["x"][0]), pos[0]))
        pos[1] = min(float(min(b["d"][1], d_hi)), max(float(max(b["d"][0], d_lo)), pos[1]))

    def _step_monsters(self, events) -> bool:
        just_finished_recoil = set()
        species_map = self.monster_cfg["species"]

        for m in sort_by_id(self.monsters):
            sp = species_map[m["kind"]]
            d_lo = float(sp["depths"][0])

            if m["state"] == "recoil":
                step_d = float(sp["recoil_dist"]) / float(sp["recoil_ticks"])
                m["pos"][0] += m["recoil_dir"][0] * step_d
                m["pos"][1] += m["recoil_dir"][1] * step_d
                self._clamp_monster(m["pos"], sp)
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m["state"] = "patrol"
                    m["state_ticks_left"] = 0
                    m["recoil_dir"] = None
                    just_finished_recoil.add(m["id"])
                continue

            dist_p = math.dist(m["pos"], self.pos)
            in_depth = self.pos[1] >= d_lo
            if m["state"] == "patrol":
                if in_depth and dist_p <= sp["detect_radius"]:
                    m["state"] = "chase"
            elif m["state"] == "chase":
                if (not in_depth) or dist_p > sp["exit_radius"]:
                    m["state"] = "patrol"

            if m["state"] == "patrol":
                wp = m["waypoints"][m["target_idx"]]
                step_d = float(sp["patrol_speed"]) / TICK
                dx, dd = wp[0] - m["pos"][0], wp[1] - m["pos"][1]
                dist_w = math.hypot(dx, dd)
                if dist_w <= step_d:
                    m["pos"][0], m["pos"][1] = float(wp[0]), float(wp[1])
                    m["target_idx"] = 1 - m["target_idx"]
                else:
                    m["pos"][0] += (dx / dist_w) * step_d
                    m["pos"][1] += (dd / dist_w) * step_d
            elif m["state"] == "chase":
                step_d = float(sp["chase_speed"]) / TICK
                dx, dd = self.pos[0] - m["pos"][0], self.pos[1] - m["pos"][1]
                dist_c = math.hypot(dx, dd)
                if dist_c > 0.0:
                    move_d = min(step_d, dist_c)
                    m["pos"][0] += (dx / dist_c) * move_d
                    m["pos"][1] += (dd / dist_c) * move_d

            self._clamp_monster(m["pos"], sp)

        if self.invuln_ticks == 0:
            hit_candidates = []
            for m in self.monsters:
                if m["state"] == "recoil" or m["id"] in just_finished_recoil:
                    continue
                sp = species_map[m["kind"]]
                if self.pos[1] < sp["depths"][0]:
                    continue
                d = math.dist(m["pos"], self.pos)
                if d <= sp["hit_radius"]:
                    hit_candidates.append((d, id_key(m["id"]), m))
            if hit_candidates:
                hit_candidates.sort(key=lambda item: (item[0], item[1]))
                hm = hit_candidates[0][2]
                sp = species_map[hm["kind"]]
                self.hp -= 1
                loss_ratio = float(self.monster_cfg.get("loss_ratio", 0.5))
                n_lost = math.floor(len(self.hold) * loss_ratio)
                lost = [item_public(self.hold.pop()) for _ in range(n_lost)]
                self.invuln_ticks = int(self.monster_cfg.get("invuln_ticks", 90))

                dx = hm["pos"][0] - self.pos[0]
                dd = hm["pos"][1] - self.pos[1]
                dist_h = math.hypot(dx, dd)
                if dist_h == 0.0:
                    rdir = [1.0, 0.0]
                else:
                    rdir = [dx / dist_h, dd / dist_h]
                hm["state"] = "recoil"
                hm["state_ticks_left"] = int(sp["recoil_ticks"])
                hm["recoil_dir"] = rdir

                events.append(("monster_hit", {
                    "monster_id": hm["id"],
                    "hp": max(0, self.hp),
                    "lost": lost,
                    "pos": list(self.pos),
                }))
                if self.hp <= 0:
                    self.hp = 0
                    rem_lost = [item_public(it) for it in reversed(self.hold)]
                    self.hold = []
                    events.append(("faint", {"cause": "monster", "lost": rem_lost, "hp": 0}))
                    self._finish("fainted", events)
                    return True
        return False

    # --- Cá bơi & sinh cá -----------------------------------------------------
    def _weighted_pick_species(self, valid_by_kind: dict, rng):
        weights = self.t["fish_weights"]
        kinds = sorted(valid_by_kind.keys())
        total = sum(float(weights[k]) for k in kinds)
        r = rng.random() * total
        acc = 0.0
        for k in kinds:
            acc += float(weights[k])
            if r <= acc:
                return k
        return kinds[-1]

    def _spawn_initial_fish(self, count: int):
        rng = self.rng.get("fish_spawn")
        xs = [float(x) for x in self.t["fish_spawn_x"]]
        depths_map = self.t["fish_spawn_depths"]
        used_pts = set()
        for _ in range(count):
            valid_by_kind = {}
            for kind in sorted(self.t["fish_weights"]):
                pts = [(x, float(d)) for x in xs for d in depths_map[kind] if (x, float(d)) not in used_pts]
                if pts:
                    valid_by_kind[kind] = pts
            if not valid_by_kind:
                break
            kind = self._weighted_pick_species(valid_by_kind, rng)
            pt = rng.choice(valid_by_kind[kind])
            used_pts.add(pt)
            hdg = rng.uniform(0.0, 360.0)
            fid = self.ids.new("F")
            self.fish.append({
                "id": fid,
                "kind": kind,
                "pos": [pt[0], pt[1]],
                "heading_deg": hdg,
                "age_ticks": 0,
            })

    def _step_fish_swim(self):
        rng = self.rng.get("fish_move")
        speed = float(self.t["fish_speed"])
        step_d = speed / TICK
        turn_ticks = int(self.t["fish_turn_ticks"])
        x_lo, x_hi = float(self.t["fish_x"][0]), float(self.t["fish_x"][1])
        depths_map = self.t["fish_depths"]

        for f in sort_by_id(self.fish):
            f["age_ticks"] += 1
            if f["age_ticks"] % turn_ticks == 0:
                f["heading_deg"] = rng.uniform(0.0, 360.0)

            d_lo, d_hi = float(depths_map[f["kind"]][0]), float(depths_map[f["kind"]][1])
            rad = math.radians(f["heading_deg"])
            vx, vd = math.cos(rad), math.sin(rad)
            nx = f["pos"][0] + vx * step_d
            nd = f["pos"][1] + vd * step_d

            if nx < x_lo:
                nx = x_lo + (x_lo - nx)
                vx = -vx
            elif nx > x_hi:
                nx = x_hi - (nx - x_hi)
                vx = -vx
            nx = min(x_hi, max(x_lo, nx))

            if nd < d_lo:
                nd = d_lo + (d_lo - nd)
                vd = -vd
            elif nd > d_hi:
                nd = d_hi - (nd - d_hi)
                vd = -vd
            nd = min(d_hi, max(d_lo, nd))

            f["pos"] = [nx, nd]
            f["heading_deg"] = math.degrees(math.atan2(vd, vx)) % 360.0

    def _maybe_spawn_fish(self, events):
        spawn_ticks = int(self.t["fish_spawn_ticks"])
        fish_max = int(self.t["fish_max"])
        if self.phase_tick <= 0 or self.phase_tick % spawn_ticks != 0:
            return
        if len(self.fish) >= fish_max:
            return

        clearance = float(self.t["fish_spawn_clearance"])
        xs = [float(x) for x in self.t["fish_spawn_x"]]
        depths_map = self.t["fish_spawn_depths"]
        valid_by_kind = {}
        for kind in sorted(self.t["fish_weights"]):
            pts = []
            for x in xs:
                for d in depths_map[kind]:
                    pt = [x, float(d)]
                    if all(math.dist(pt, ef["pos"]) > clearance for ef in self.fish):
                        pts.append(pt)
            if pts:
                valid_by_kind[kind] = pts
        if not valid_by_kind:
            return

        rng = self.rng.get("fish_spawn")
        kind = self._weighted_pick_species(valid_by_kind, rng)
        pt = rng.choice(valid_by_kind[kind])
        hdg = rng.uniform(0.0, 360.0)
        fid = self.ids.new("F")
        self.fish.append({
            "id": fid,
            "kind": kind,
            "pos": [pt[0], pt[1]],
            "heading_deg": hdg,
            "age_ticks": 0,
        })
        events.append(("fish_spawned", {"id": fid, "kind": kind, "pos": [pt[0], pt[1]]}))

    # --- tiện ích -------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
