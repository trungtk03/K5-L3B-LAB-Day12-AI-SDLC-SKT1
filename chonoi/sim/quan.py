"""Buổi tối — Mở Quán (`quan`).

Hoàn thiện Lát 3 & Lát 4 theo PRD-0 mục F ("Quán") và Test Contract v1.0:
  - Lát 3: Khách đến theo lịch, kiểm tra nguyên liệu khả dụng, giữ chỗ (reserved),
           kiên nhẫn, rời quán (customer_left), no_dish, vòng đời khách.
  - Lát 4: Tương tác bếp/bàn (cook_started, dish_ready, dish_picked, served),
           khách ăn xong trả tiền (paid), boa (tip), uy tín, đóng ca (quan_end).
"""

import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids

        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0

        # Kho: nạp từ file --inventory HOẶC scenario.stock
        raw_stock = inventory if inventory is not None else scenario.get("stock", {})
        self.stock = {k: v for k, v in raw_stock.items() if v > 0}

        raw_hand = scenario.get("hand")
        if raw_hand is not None:
            self.hand = dict(raw_hand)
            if "base_price" not in self.hand or self.hand["base_price"] is None:
                self.hand["base_price"] = int(self.menu[self.hand["dish_id"]]["price"])
            ids.reserve(self.hand["order_id"])
        else:
            self.hand = None

        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = scenario.get("phase_tick", 0)
        self.random_customers = scenario.get("random_customers", True)
        self.reputation = float(scenario.get("reputation", t["reputation_initial"]))

        self.stoves = []
        for s in self._merge(t["stoves"], scenario.get("stoves", [])):
            st = dict(s)
            st["pos"] = [float(c) for c in st["pos"]]
            st.setdefault("state", "idle")
            st.setdefault("dish", None)
            st.setdefault("order_id", None)
            st.setdefault("cook_ticks_left", 0)
            st.setdefault("ready_ticks", 0)
            if st["state"] in ("cooking", "ready"):
                if st.get("base_price") is None and st["dish"] in self.menu:
                    st["base_price"] = int(self.menu[st["dish"]]["price"])
                if st.get("order_id"):
                    ids.reserve(st["order_id"])
            else:
                st.setdefault("base_price", None)
            self.stoves.append(st)

        self.tables = []
        for tb in self._merge(t["tables"], scenario.get("tables", [])):
            tcopy = dict(tb)
            tcopy["pos"] = [float(c) for c in tcopy["pos"]]
            self.tables.append(tcopy)

        # Đếm số món đang gắn với mỗi order_id (trên bếp đang nấu/chín hoặc trên tay)
        assigned_counts = {}
        for s in self.stoves:
            if s["state"] in ("cooking", "ready") and s.get("order_id"):
                oid = s["order_id"]
                assigned_counts[oid] = assigned_counts.get(oid, 0) + 1
        if self.hand is not None:
            oid = self.hand["order_id"]
            assigned_counts[oid] = assigned_counts.get(oid, 0) + 1

        # Khách hàng dựng sẵn từ scenario & suy ra giữ chỗ (reserved) + kiểm mâu thuẫn mức luật
        default_patience = int(round(t["patience_s"] * TICK))
        default_eat = int(round(t["eat_s"] * TICK))
        self.customers = []
        for raw_c in scenario.get("customers", []):
            c = dict(raw_c)
            cid = c["id"]
            ids.reserve(cid)
            dish_id = c["dish_id"]
            state = c.get("state", "waiting")
            c["state"] = state
            c.setdefault("order_tick", 0)
            cnt = assigned_counts.get(cid, 0)

            if state == "eating":
                c["order_status"] = "served"
                c["reserved"] = {}
                c.setdefault("patience_ticks_left", 0)
                c.setdefault("eat_ticks_left", default_eat)
                if cnt != 0:
                    raise BadInput(f"customers.{cid}: khách đang ăn không thể còn món trên bếp/tay")
            else:
                c.setdefault("patience_ticks_left", default_patience)
                c.setdefault("eat_ticks_left", 0)
                if "order_status" in raw_c:
                    order_status = raw_c["order_status"]
                else:
                    order_status = "assigned" if cnt > 0 else "reserved"
                c["order_status"] = order_status

                if order_status == "assigned":
                    if cnt != 1:
                        raise BadInput(f"customers.{cid}: đơn assigned phải có đúng một món trên bếp hoặc trên tay (đang có {cnt})")
                    if raw_c.get("reserved"):
                        raise BadInput(f"customers.{cid}: đơn assigned không được còn giữ chỗ nguyên liệu")
                    c["reserved"] = {}
                else:  # reserved
                    if cnt != 0:
                        raise BadInput(f"customers.{cid}: đơn reserved không được đang có món trên bếp hoặc trên tay")
                    if "reserved" in raw_c:
                        res = {k: v for k, v in sorted(raw_c["reserved"].items()) if v > 0}
                    else:
                        recipe = self.menu[dish_id]["recipe"]
                        res = {k: recipe[k] for k in sorted(recipe)}
                    c["reserved"] = res
            self.customers.append(c)

        # Kiểm tổng nguyên liệu giữ chỗ không vượt kho hiện có
        total_reserved = {}
        for c in self.customers:
            for k, qty in c["reserved"].items():
                total_reserved[k] = total_reserved.get(k, 0) + qty
        for k, qty in total_reserved.items():
            if qty > self.stock.get(k, 0):
                raise BadInput(f"khách giữ chỗ nguyên liệu {k} ({qty}) vượt kho hiện có ({self.stock.get(k, 0)})")

        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": list(self.pos)},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": dict(self.hand) if self.hand is not None else None,
            "stoves": [
                {k: s.get(k) for k in ("id", "pos", "state", "dish", "order_id", "cook_ticks_left", "ready_ticks")}
                for s in self.stoves
            ],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # BƯỚC 1: Cập nhật bếp & timer
        for s in sort_by_id(self.stoves):
            if s["state"] == "ready":
                s["ready_ticks"] += 1
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
                if s["cook_ticks_left"] == 0:
                    s["state"] = "ready"
                    s["ready_ticks"] = 0
                    events.append(("dish_ready", {
                        "stove_id": s["id"],
                        "order_id": s["order_id"],
                        "dish_id": s["dish"],
                    }))

        for c in self.customers:
            if c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
            elif c["state"] == "waiting":
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)

        # Di chuyển người chơi và chặn biên
        self._move(inp)

        # BƯỚC 2: Tương tác (interact) tại bếp hoặc bàn (tối đa 1 đối tượng mỗi bước)
        if inp.pressed("interact"):
            self._handle_interact(events)

        # BƯỚC 3: Khách ăn xong hoặc hết kiên nhẫn (duyệt theo thứ tự id bàn)
        to_remove = set()
        for c in sort_by_id(list(self.customers), key=lambda x: x["table_id"]):
            if c["state"] == "eating" and c["eat_ticks_left"] == 0:
                self._pay_customer(c, "finished_eating", events)
                to_remove.add(c["id"])
            elif self.time_left_ticks > 0 and c["state"] == "waiting" and c["patience_ticks_left"] == 0:
                self._adjust_reputation(self.t["left_reputation_delta"])
                events.append(("customer_left", {
                    "order_id": c["id"],
                    "table_id": c["table_id"],
                    "reason": "patience",
                    "reputation": self.reputation,
                }))
                to_remove.add(c["id"])
        if to_remove:
            self.customers = [c for c in self.customers if c["id"] not in to_remove]

        # BƯỚC 4: Khách mới theo lịch
        if self.random_customers and self.time_left_ticks > 0:
            self._maybe_spawn_customer(events)

        # BƯỚC 5: Kết thúc ca (quan_end)
        if self.time_left_ticks <= 0:
            for c in sort_by_id(list(self.customers), key=lambda x: x["table_id"]):
                if c["state"] == "eating":
                    self._pay_customer(c, "closing", events)
                elif c["state"] == "waiting":
                    events.append(("customer_left", {
                        "order_id": c["id"],
                        "table_id": c["table_id"],
                        "reason": "closing",
                        "reputation": self.reputation,
                    }))
            self.customers = []
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {
                "reason": "time",
                "money": self.money,
                "earned": self.earned,
                "shift_earned": self.shift_earned,
                "reputation": self.reputation,
            }))
        return events

    # --- tiện ích ---------------------------------------------------------------
    def _adjust_reputation(self, delta: float):
        lo = float(self.t["reputation_min"])
        hi = float(self.t["reputation_max"])
        self.reputation = round(min(hi, max(lo, self.reputation + delta)), 6)

    def _pay_customer(self, c, reason: str, events: list):
        base_price = int(c["base_price"])
        tip = int(c["tip"])
        amount = base_price + tip
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if tip > 0:
            self._adjust_reputation(self.t["tip_reputation"])
        events.append(("paid", {
            "order_id": c["id"],
            "table_id": c["table_id"],
            "base_price": base_price,
            "tip": tip,
            "amount": amount,
            "reason": reason,
        }))

    def _oldest_reserved_customer(self):
        reserved = [
            c for c in self.customers
            if c["state"] == "waiting" and c.get("order_status") == "reserved"
        ]
        if not reserved:
            return None
        reserved.sort(key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"]), id_key(c["id"])))
        return reserved[0]

    def _customer_at_table(self, table_id: str):
        for c in self.customers:
            if c["table_id"] == table_id:
                return c
        return None

    def _handle_interact(self, events: list):
        rad = self.t["interact_radius"]
        oldest_reserved = self._oldest_reserved_customer()
        candidates = []

        for s in self.stoves:
            d = math.dist(self.pos, s["pos"])
            if d <= rad:
                can_cook = s["state"] == "idle" and oldest_reserved is not None
                can_pick = s["state"] == "ready" and self.hand is None
                if can_cook or can_pick:
                    candidates.append((d, 0, id_key(s["id"]), "stove", s))

        if self.hand is not None:
            for tb in self.tables:
                d = math.dist(self.pos, tb["pos"])
                if d <= rad:
                    c = self._customer_at_table(tb["id"])
                    if c is not None and c["state"] == "waiting" and c["id"] == self.hand["order_id"]:
                        candidates.append((d, 1, id_key(tb["id"]), "table", tb))

        if not candidates:
            return

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        _, _, _, kind, target = candidates[0]

        if kind == "stove":
            if target["state"] == "idle":
                c = oldest_reserved
                dish_id = c["dish_id"]
                dish_cfg = self.menu[dish_id]
                recipe = dict(c["reserved"]) if c["reserved"] else dict(dish_cfg["recipe"])
                for k, qty in recipe.items():
                    new_qty = self.stock.get(k, 0) - qty
                    if new_qty > 0:
                        self.stock[k] = new_qty
                    else:
                        self.stock.pop(k, None)
                base_price = int(dish_cfg["price"])
                c["reserved"] = {}
                c["order_status"] = "assigned"
                c["base_price"] = base_price
                target["state"] = "cooking"
                target["dish"] = dish_id
                target["order_id"] = c["id"]
                target["base_price"] = base_price
                target["cook_ticks_left"] = int(round(dish_cfg["cook_s"] * TICK))
                target["ready_ticks"] = 0
                events.append(("cook_started", {
                    "stove_id": target["id"],
                    "order_id": c["id"],
                    "dish_id": dish_id,
                    "items": {k: recipe[k] for k in sorted(recipe)},
                    "base_price": base_price,
                }))
            elif target["state"] == "ready" and self.hand is None:
                order_id = target["order_id"]
                dish_id = target["dish"]
                base_price = target.get("base_price")
                if base_price is None:
                    base_price = int(self.menu[dish_id]["price"])
                self.hand = {
                    "order_id": order_id,
                    "dish_id": dish_id,
                    "base_price": int(base_price),
                }
                target["state"] = "idle"
                target["dish"] = None
                target["order_id"] = None
                target["base_price"] = None
                target["cook_ticks_left"] = 0
                target["ready_ticks"] = 0
                events.append(("dish_picked", {
                    "stove_id": target["id"],
                    "order_id": order_id,
                    "dish_id": dish_id,
                }))
        else:  # table
            c = self._customer_at_table(target["id"])
            hand = self.hand
            base_price = int(hand["base_price"])
            dish_id = hand["dish_id"]
            patience_max = int(round(self.t["patience_s"] * TICK))
            if patience_max > 0 and (c["patience_ticks_left"] / patience_max) >= self.t["tip_min_patience_ratio"]:
                tip = math.floor(base_price * self.t["tip_rate"])
            else:
                tip = 0
            c["state"] = "eating"
            c["order_status"] = "served"
            c["base_price"] = base_price
            c["tip"] = tip
            c["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
            self.hand = None
            events.append(("served", {
                "order_id": c["id"],
                "table_id": target["id"],
                "dish_id": dish_id,
                "patience_ticks_left": c["patience_ticks_left"],
                "base_price": base_price,
                "tip": tip,
            }))

    def _maybe_spawn_customer(self, events: list):
        first_tick = int(self.t["first_customer_tick"])
        interval_ticks = int(round(self.t["customer_interval_s"] * TICK))
        if self.phase_tick < first_tick:
            return
        if self.phase_tick != first_tick and (self.phase_tick - first_tick) % interval_ticks != 0:
            return

        occupied = {c["table_id"] for c in self.customers}
        free_tables = [tb for tb in sort_by_id(self.tables) if tb["id"] not in occupied]
        if not free_tables:
            return
        tb = free_tables[0]

        # Tính nguyên liệu khả dụng = tồn kho - tổng đang được khách giữ chỗ
        avail = dict(self.stock)
        for c in self.customers:
            for k, qty in c.get("reserved", {}).items():
                avail[k] = avail.get(k, 0) - qty

        dishes_eligible = []
        for dish_id in sorted(self.menu):
            recipe = self.menu[dish_id]["recipe"]
            if all(avail.get(k, 0) >= qty for k, qty in recipe.items()):
                dishes_eligible.append(dish_id)

        if not dishes_eligible:
            events.append(("no_dish", {}))
            return

        dish_id = self.rng.get("customer").choice(dishes_eligible)
        c_id = self.ids.new("C")
        recipe = self.menu[dish_id]["recipe"]
        cust = {
            "id": c_id,
            "table_id": tb["id"],
            "dish_id": dish_id,
            "order_tick": self.phase_tick,
            "state": "waiting",
            "order_status": "reserved",
            "patience_ticks_left": int(round(self.t["patience_s"] * TICK)),
            "eat_ticks_left": 0,
            "reserved": {k: recipe[k] for k in sorted(recipe)},
        }
        self.customers.append(cust)
        events.append(("customer_arrived", {
            "order_id": c_id,
            "table_id": tb["id"],
            "dish_id": dish_id,
        }))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
