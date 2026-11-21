"""Chế độ Vòng Ngày (`day`, Contract v1.1): gather -> quan -> shop qua 1..5 Ngày.

Thứ tự đổi pha (mục 4.5):
  - Đầu Ngày: `day_start` -> `day_plan` -> `phase_start` (gather, tick 0 hoặc cùng tick sau shop_end).
  - Sau `gather_end`: dựng `QuanSim` với kho bàn giao (kể cả khi `fainted` -> kho rỗng) và phát `phase_start` (quan) cùng tick.
  - Sau `quan_end`: dựng `ShopSim` và phát `phase_start` (shop) cùng tick.
  - Sau `shop_end`: tăng `days_completed`; nếu đủ `--days` thì kết thúc (`days_complete`),
    ngược lại sao `upgrades -> active_upgrades`, tăng `day` và dựng Ngày mới cùng tick.
"""

import copy

from ..contract import compute_plan_ingredients
from ..ids import IdAllocator
from .gather import GatherSim
from .quan import QuanSim
from .shop import ShopSim


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.rng = streams
        self.total_days = int(days)

        day_blk = scenario.get("day", {}) if isinstance(scenario, dict) else {}
        self.gather_tpl = copy.deepcopy(scenario.get("gather", {})) if isinstance(scenario, dict) else {}
        self.quan_tpl = copy.deepcopy(scenario.get("quan", {})) if isinstance(scenario, dict) else {}

        self.money = int(day_blk.get("money", 0))
        self.earned = int(day_blk.get("earned", self.money))
        self.reputation = float(day_blk.get("reputation", tuning["quan"]["reputation_initial"]))

        init_up = {k: int(v) for k, v in sorted(day_blk.get("upgrades", {}).items()) if int(v) > 0}
        self.upgrades = dict(init_up)
        self.active_upgrades = dict(init_up)

        # Kế hoạch D1..D5 (cho phép ghi đè theo số Ngày từ scenario.day.day_plan)
        self.day_plans = {}
        for entry in tuning["day_plan"]:
            dnum = int(entry["day"])
            dishes = {k: int(entry["dishes"][k]) for k in sorted(entry["dishes"])}
            ings = {k: int(entry["ingredients"][k]) for k in sorted(entry["ingredients"])}
            self.day_plans[dnum] = {"dishes": dishes, "ingredients": ings}
        for entry in day_blk.get("day_plan", []):
            dnum = int(entry["day"])
            dishes = {k: int(entry["dishes"][k]) for k in sorted(entry["dishes"])}
            ings = compute_plan_ingredients(dishes, tuning["menu"])
            self.day_plans[dnum] = {"dishes": dishes, "ingredients": ings}

        self.day = 1
        self.days_completed = 0
        self.done = False
        self.reason = None
        self.sub = None
        self._init_events = []

        self._start_gather_day(self.day, self._init_events)

    @property
    def phase(self) -> str:
        return self.sub.phase

    @property
    def phase_tick(self) -> int:
        return self.sub.phase_tick

    @property
    def time_left_ticks(self) -> int:
        return self.sub.time_left_ticks

    def current_plan(self) -> dict:
        p = self.day_plans[self.day]
        return {
            "dishes": dict(p["dishes"]),
            "ingredients": dict(p["ingredients"]),
        }

    def pop_init_events(self) -> list:
        evs, self._init_events = self._init_events, []
        return evs

    def _start_gather_day(self, day_num: int, out_events: list):
        self.day = day_num
        self.sub = GatherSim(
            self.tuning,
            copy.deepcopy(self.gather_tpl),
            self.rng,
            IdAllocator(),
            day=day_num,
            active_upgrades=self.active_upgrades,
            money=self.money,
            earned=self.earned,
            reputation=self.reputation,
        )
        plan = self.current_plan()
        out_events.append(("gather", day_num, "day_start", {}))
        out_events.append(("gather", day_num, "day_plan", plan))
        out_events.append(("gather", day_num, "phase_start", {}))

    def snapshot(self) -> dict:
        snap = self.sub.snapshot()
        snap["day"] = self.day
        snap["day_plan"] = self.current_plan()
        snap["upgrades"] = {k: self.upgrades[k] for k in sorted(self.upgrades)}
        snap["active_upgrades"] = {k: self.active_upgrades[k] for k in sorted(self.active_upgrades)}
        return snap

    def step(self, inp) -> list:
        cur_phase = self.sub.phase
        cur_day = self.day
        sub_events = self.sub.step(inp)
        out = [(cur_phase, cur_day, name, data) for name, data in sub_events]

        if cur_phase == "gather" and self.sub.done:
            inv = self.sub.inventory_items()
            plan = self.current_plan()
            self.sub = QuanSim(
                self.tuning,
                copy.deepcopy(self.quan_tpl),
                self.rng,
                IdAllocator(),
                inventory=inv,
                allowed_dishes=set(plan["dishes"].keys()),
                money=self.money,
                earned=self.earned,
                reputation=self.reputation,
            )
            out.append(("quan", cur_day, "phase_start", {}))

        elif cur_phase == "quan" and self.sub.done:
            self.money = self.sub.money
            self.earned = self.sub.earned
            self.reputation = self.sub.reputation
            leftover = dict(self.sub.stock)
            self.sub = ShopSim(
                self.tuning,
                leftover,
                self.money,
                self.earned,
                self.reputation,
                self.upgrades,
            )
            out.append(("shop", cur_day, "phase_start", {}))

        elif cur_phase == "shop" and self.sub.done:
            self.money = self.sub.money
            self.upgrades = {k: int(v) for k, v in sorted(self.sub.upgrades.items()) if int(v) > 0}
            self.days_completed += 1
            if self.days_completed >= self.total_days:
                self.done = True
                self.reason = "days_complete"
            else:
                self.active_upgrades = dict(self.upgrades)
                self._start_gather_day(self.day + 1, out)

        else:
            # Đồng bộ money/earned/reputation liên tục để snapshot luôn chính xác trong mọi pha
            self.money = self.sub.money
            self.earned = self.sub.earned
            self.reputation = self.sub.reputation
            if cur_phase == "shop":
                self.upgrades = {k: int(v) for k, v in sorted(self.sub.upgrades.items()) if int(v) > 0}

        return out
