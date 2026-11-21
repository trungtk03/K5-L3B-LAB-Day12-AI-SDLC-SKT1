"""Soak headless nhiều Ngày bằng bot tất định (Contract v1.3).

    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Chạy `--days N` Ngày liên tiếp trong một tiến trình headless (`gather -> quan -> shop`),
lặp kế hoạch D1–D5 ở Ngày 6–10+, giữ xuyên suốt money, earned, reputation, upgrades, day và id cá thể.
Xuất soak.json: {days, days_completed, crashes, results: [{day, earned, reputation, score}], duration_s}.
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time

from .contract import load_contract
from .errors import BadInput
from .ids import id_key, sort_by_id
from .inputs import BUTTONS_V11, InputState, normalize
from .runner import Session


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


class DeterministicBot:
    """Bot tất định điều khiển Út Sen qua cả 3 pha gather -> quan -> shop."""

    def __init__(self, tuning):
        self.tuning = tuning
        self.held = {b: False for b in BUTTONS_V11}

    def _emit(self, move=(0.0, 0.0), interact=False, catch=False, shop_done=False, buy=None) -> InputState:
        wanted = {"interact": interact, "catch": catch, "pause": False, "shop_done": shop_done}
        edges = set()
        for b, v in wanted.items():
            if v and not self.held[b]:
                edges.add(b)
            self.held[b] = v
        return InputState(normalize(move), dict(self.held), edges, buy=buy)

    @staticmethod
    def _dir_to(src, dst):
        dx, dy = dst[0] - src[0], dst[1] - src[1]
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return (0.0, 0.0)
        return (dx / dist, dy / dist)

    def decide(self, day_sim) -> InputState:
        phase = day_sim.phase
        sub = day_sim.sub
        if phase == "gather":
            return self._decide_gather(day_sim, sub)
        if phase == "quan":
            return self._decide_quan(sub)
        return self._decide_shop(day_sim, sub)

    def _decide_gather(self, day_sim, g) -> InputState:
        plan = day_sim.current_plan()
        need_ings = plan["ingredients"]
        menu = self.tuning["menu"]

        # Đếm hàng còn tươi trong giỏ
        have = {}
        for it in g.hold:
            if it["fresh_frac"] >= g.spoiled_below:
                have[it["kind"]] = have.get(it["kind"], 0) + 1

        # Kiểm xem đã nấu được ít nhất 1 món trong kế hoạch chưa
        can_cook_one = any(
            all(have.get(k, 0) >= q for k, q in menu[d]["recipe"].items())
            for d in sorted(plan["dishes"])
        )
        should_dock = (
            (can_cook_one and len(g.hold) >= 4)
            or len(g.hold) >= g.t["hold_capacity"] - 1
            or g.phase_tick >= 1800
            or g.time_left_ticks <= 900
            or g.hp <= 1
        )
        if should_dock:
            dock = g.t["dock_pos"]
            if math.dist(g.pos, dock) <= g.t["dock_radius"]:
                return self._emit((0.0, 0.0), interact=not self.held["interact"])
            return self._emit(self._dir_to(g.pos, dock))

        # Hồi oxy nếu dưới 45%
        if g.oxygen_ticks < g.oxygen_max * 0.45:
            return self._emit((0.0, -1.0))

        # Thiếu nguyên liệu nào theo kế hoạch
        missing = {k: need_ings[k] - have.get(k, 0) for k in sorted(need_ings) if have.get(k, 0) < need_ings[k]}

        # Ưu tiên hái nút mặt nước cần thiết
        ready_nodes = [
            n for n in sort_by_id(g.nodes)
            if n["regrow_ticks"] == 0 and n["kind"] in missing
        ]
        if ready_nodes:
            ready_nodes.sort(key=lambda n: (math.dist(g.pos, n["pos"]), id_key(n["id"])))
            target = ready_nodes[0]
            if g.pos[1] <= g.t["surface_depth"] and math.dist(g.pos, target["pos"]) <= g.t["interact_radius"]:
                return self._emit((0.0, 0.0), interact=not self.held["interact"])
            return self._emit(self._dir_to(g.pos, target["pos"]))

        # Sau đó lặn bắt đàn cá cần thiết (đủ chỗ giỏ, tránh gần Cá Sấu)
        free_slots = g.t["hold_capacity"] - len(g.hold)
        cand_fish = [
            f for f in sort_by_id(g.fish)
            if f["kind"] in missing and g.t["fish_yield"][f["kind"]] <= free_slots
        ]
        if cand_fish:
            cand_fish.sort(key=lambda f: (math.dist(g.pos, f["pos"]), id_key(f["id"])))
            target = cand_fish[0]
            if g.pos[1] > g.t["surface_depth"] and math.dist(g.pos, target["pos"]) <= g.t["catch_radius"] and g.catch_cd_ticks == 0:
                return self._emit((0.0, 0.0), catch=not self.held["catch"])
            return self._emit(self._dir_to(g.pos, target["pos"]))

        # Không còn mục tiêu phù hợp -> về bến
        dock = g.t["dock_pos"]
        if math.dist(g.pos, dock) <= g.t["dock_radius"]:
            return self._emit((0.0, 0.0), interact=not self.held["interact"])
        return self._emit(self._dir_to(g.pos, dock))

    def _decide_quan(self, q) -> InputState:
        rad = q.t["interact_radius"]

        # 1. Đang cầm món -> đem tới bàn của khách đó
        if q.hand is not None:
            cust = next((c for c in q.customers if c["id"] == q.hand["order_id"]), None)
            if cust is not None:
                tb = next(t for t in q.tables if t["id"] == cust["table_id"])
                if math.dist(q.pos, tb["pos"]) <= rad:
                    return self._emit((0.0, 0.0), interact=not self.held["interact"])
                return self._emit(self._dir_to(q.pos, tb["pos"]))

        # 2. Tay trống & có bếp ready -> tới nhấc món
        if q.hand is None:
            ready_stoves = [s for s in sort_by_id(q.stoves) if s["state"] == "ready"]
            if ready_stoves:
                ready_stoves.sort(key=lambda s: (math.dist(q.pos, s["pos"]), id_key(s["id"])))
                st = ready_stoves[0]
                if math.dist(q.pos, st["pos"]) <= rad:
                    return self._emit((0.0, 0.0), interact=not self.held["interact"])
                return self._emit(self._dir_to(q.pos, st["pos"]))

        # 3. Có đơn reserved & có bếp idle -> tới bật bếp nấu
        has_reserved = any(c["state"] == "waiting" and c.get("order_status") == "reserved" for c in q.customers)
        if has_reserved:
            idle_stoves = [s for s in sort_by_id(q.stoves) if s["state"] == "idle"]
            if idle_stoves:
                idle_stoves.sort(key=lambda s: (math.dist(q.pos, s["pos"]), id_key(s["id"])))
                st = idle_stoves[0]
                if math.dist(q.pos, st["pos"]) <= rad:
                    return self._emit((0.0, 0.0), interact=not self.held["interact"])
                return self._emit(self._dir_to(q.pos, st["pos"]))

        # 4. Đứng chờ gần bếp B1
        b1 = q.stoves[0]["pos"]
        if math.dist(q.pos, b1) > 0.5:
            return self._emit(self._dir_to(q.pos, b1))
        return self._emit((0.0, 0.0))

    def _decide_shop(self, day_sim, s) -> InputState:
        up_cfg = self.tuning["shop"]["upgrades"]
        for uid in ("oxygen", "hp"):
            cur = s.upgrades.get(uid, 0)
            nxt = next((t for t in up_cfg[uid] if t["level"] == cur + 1), None)
            if nxt is not None and s.money >= int(nxt["price"]):
                return self._emit(buy=uid)
        return self._emit(shop_done=not self.held["shop_done"])


def _write_json_atomic(path: str, payload: dict):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".soak-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run_soak(seed: int, days: int) -> dict:
    t0 = time.perf_counter()
    tuning = load_contract()["tuning"]
    mult = tuning["score"]["reputation_multiplier"]
    sess = Session("day", tuning, {"day": {}, "gather": {}, "quan": {}}, seed, days=days)
    bot = DeterministicBot(tuning)

    results = []
    crashes = 0
    max_ticks = days * 22_500

    try:
        while not sess.done and sess.tick < max_ticks:
            inp = bot.decide(sess.sim)
            evs = sess.step(inp)
            for ev in evs:
                if ev["name"] == "shop_end":
                    sim = sess.sim
                    score = sim.earned + mult * math.floor(sim.reputation)
                    results.append({
                        "day": ev["day"],
                        "earned": sim.earned,
                        "reputation": round(sim.reputation, 3),
                        "score": score,
                    })
    except Exception:
        crashes += 1

    duration_s = round(time.perf_counter() - t0, 3)
    return {
        "days": days,
        "days_completed": sess.sim.days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": duration_s,
    }


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak", description="Soak headless nhiều Ngày (Contract v1.3).")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.days < 1:
            raise BadInput("--days phải >= 1")
        result = run_soak(a.seed, a.days)
        _write_json_atomic(a.out, result)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
