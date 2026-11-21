"""Buổi tối — Mở Quán (`quan`, Contract v1.2).

Hoàn thiện Phase 1 + Phase 2 + Phase 3 (Độ tươi, giữ chỗ theo id cá thể, giá theo độ tươi):
  - Kho là mảng cá thể `{id, kind, fresh_frac}`, hao `-0.25/s` (`-1/240` mỗi tick, kể cả hàng đang giữ).
  - Phát `spoiled` theo `id` khi đi từ `>= 30` xuống `< 30`; đơn bị ảnh hưởng nhả toàn bộ giữ chỗ và thử giữ lại đúng 1 lần theo `(order_tick, table_id)`, thất bại chuyển `unfulfillable`.
  - Giữ chỗ theo id: mỗi loại lấy cá thể chưa ươn tươi nhất, hòa theo `id`.
  - Giá chốt khi `cook_started`: `base_price = floor(giá niêm yết × avg_fresh / 100)`; boa áp trên `base_price` đã chốt; `cook_started.data.items` là mảng cá thể sắp theo `(kind, id)`.
"""

from fractions import Fraction
import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import item_public, make_item, to_fraction
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None,
                 allowed_dishes=None, money=0, earned=0, reputation=None):
        t = tuning["quan"]
        fr = tuning["freshness"]
        self.t = t
        self.menu = tuning["menu"]
        self.allowed_dishes = set(allowed_dishes) if allowed_dishes is not None else set(self.menu.keys())
        self.rng = streams
        self.ids = ids

        self.fresh_decay = to_fraction(fr["quan_decay_per_s"]) / Fraction(60)
        self.spoiled_below = to_fraction(fr["spoiled_below"])

        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0

        # Kho cá thể: nạp từ --inventory (hoặc từ gather trong day) HOẶC scenario.stock
        raw_stock = inventory if inventory is not None else scenario.get("stock", [])
        self.stock = []
        seen_item_ids = set()
        for raw_it in raw_stock:
            iid = raw_it["id"]
            if iid in seen_item_ids:
                raise BadInput(f"trùng id cá thể trong kho quán: {iid!r}")
            seen_item_ids.add(iid)
            ff = raw_it["fresh_frac"] if "fresh_frac" in raw_it else raw_it["fresh"]
            self.stock.append(make_item(iid, raw_it["kind"], ff))
            ids.reserve(iid)
        self.stock = sort_by_id(self.stock)

        raw_hand = scenario.get("hand")
        if raw_hand is not None:
            self.hand = dict(raw_hand)
            if self.hand["dish_id"] not in self.allowed_dishes:
                raise BadInput(f"quan.hand.dish_id ({self.hand['dish_id']}) không thuộc kế hoạch Ngày")
            if "base_price" not in self.hand or self.hand["base_price"] is None:
                self.hand["base_price"] = int(self.menu[self.hand["dish_id"]]["price"])
            ids.reserve(self.hand["order_id"])
        else:
            self.hand = None

        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.phase_tick = scenario.get("phase_tick", 0)
        self.random_customers = scenario.get("random_customers", True)
        self.reputation = float(reputation if reputation is not None else scenario.get("reputation", t["reputation_initial"]))

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
                if st["dish"] not in self.allowed_dishes:
                    raise BadInput(f"stoves.{st['id']}.dish ({st['dish']}) không thuộc kế hoạch Ngày")
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

        # Đếm số món đang gắn với mỗi order_id (trên bếp hoặc trên tay)
        assigned_counts = {}
        for s in self.stoves:
            if s["state"] in ("cooking", "ready") and s.get("order_id"):
                oid = s["order_id"]
                assigned_counts[oid] = assigned_counts.get(oid, 0) + 1
        if self.hand is not None:
            oid = self.hand["order_id"]
            assigned_counts[oid] = assigned_counts.get(oid, 0) + 1

        # Khách hàng dựng sẵn từ scenario + kiểm/cấp giữ chỗ theo id cá thể
        default_patience = int(round(t["patience_s"] * TICK))
        default_eat = int(round(t["eat_s"] * TICK))
        self.customers = []
        needs_auto_reserve = []
        used_reserved_ids = set()
        stock_by_id = {it["id"]: it for it in self.stock}

        for raw_c in scenario.get("customers", []):
            c = dict(raw_c)
            cid = c["id"]
            ids.reserve(cid)
            dish_id = c["dish_id"]
            if dish_id not in self.allowed_dishes:
                raise BadInput(f"customers.{cid}: dish_id ({dish_id}) không thuộc kế hoạch Ngày")
            state = c.get("state", "waiting")
            c["state"] = state
            c.setdefault("order_tick", 0)
            cnt = assigned_counts.get(cid, 0)

            if state == "eating":
                c["order_status"] = "served"
                c["reserved"] = []
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
                        raise BadInput(f"customers.{cid}: đơn assigned phải có đúng một món trên bếp/tay (đang có {cnt})")
                    if raw_c.get("reserved"):
                        raise BadInput(f"customers.{cid}: đơn assigned không được còn giữ chỗ")
                    c["reserved"] = []
                elif order_status == "unfulfillable":
                    if cnt != 0:
                        raise BadInput(f"customers.{cid}: đơn unfulfillable không được có món trên bếp/tay")
                    if raw_c.get("reserved"):
                        raise BadInput(f"customers.{cid}: đơn unfulfillable không được còn giữ chỗ")
                    c["reserved"] = []
                else:  # reserved
                    if cnt != 0:
                        raise BadInput(f"customers.{cid}: đơn reserved không được đang có món trên bếp/tay")
                    if "reserved" in raw_c:
                        res_ids = list(raw_c["reserved"])
                        self._validate_explicit_reserved(cid, dish_id, res_ids, stock_by_id, used_reserved_ids)
                        c["reserved"] = sorted(res_ids, key=id_key)
                    else:
                        c["reserved"] = []
                        needs_auto_reserve.append(c)
            self.customers.append(c)

        # Cấp giữ chỗ cho các đơn reserved chưa khai mảng reserved theo (order_tick, id bàn)
        needs_auto_reserve.sort(key=lambda c: (c["order_tick"], id_key(c["table_id"]), id_key(c["id"])))
        for c in needs_auto_reserve:
            picked = self._pick_reserve_ids(c["dish_id"])
            if picked is None:
                raise BadInput(f"customers.{c['id']}: không đủ nguyên liệu chưa ươn trong kho cho {c['dish_id']}")
            c["reserved"] = picked

        self.money = int(money)
        self.earned = int(earned)
        self.shift_earned = 0
        self.done = False
        self.reason = None

    def _validate_explicit_reserved(self, cid, dish_id, res_ids, stock_by_id, used_reserved_ids):
        recipe = self.menu[dish_id]["recipe"]
        counts = {}
        for rid in res_ids:
            if rid not in stock_by_id:
                raise BadInput(f"customers.{cid}.reserved: id cá thể {rid!r} không có trong kho")
            if rid in used_reserved_ids:
                raise BadInput(f"customers.{cid}.reserved: id cá thể {rid!r} bị dùng chung giữa hai đơn")
            it = stock_by_id[rid]
            if it["fresh_frac"] < self.spoiled_below:
                raise BadInput(f"customers.{cid}.reserved: cá thể {rid!r} đã ươn (fresh < {self.spoiled_below})")
            used_reserved_ids.add(rid)
            counts[it["kind"]] = counts.get(it["kind"], 0) + 1
        if counts != recipe:
            raise BadInput(f"customers.{cid}.reserved: cá thể giữ chỗ ({counts}) không khớp công thức {dish_id} ({recipe})")

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
            "stock": [item_public(it) for it in sort_by_id(self.stock)],
            "hand": dict(self.hand) if self.hand is not None else None,
            "stoves": [
                {k: s.get(k) for k in ("id", "pos", "state", "dish", "order_id", "cook_ticks_left", "ready_ticks")}
                for s in self.stoves
            ],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    # --- một bước (đúng thứ tự Contract v1.2 mục 1) ---------------------------
    def step(self, inp):
        events = []

        # 1. Đồng hồ và timer
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        for s in sort_by_id(self.stoves):
            if s["state"] == "ready":
                s["ready_ticks"] += 1
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
        for c in self.customers:
            if c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
            elif c["state"] == "waiting":
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)

        # 2. Hao tươi kho thô (kể cả hàng đang giữ), phát hết spoiled theo id rồi xử lý giữ chỗ bị ươn
        newly_spoiled = []
        for it in self.stock:
            prev = it["fresh_frac"]
            now = max(Fraction(0), prev - self.fresh_decay)
            it["fresh_frac"] = now
            if prev >= self.spoiled_below and now < self.spoiled_below:
                newly_spoiled.append(it)
        if newly_spoiled:
            for it in sort_by_id(newly_spoiled):
                events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": "stock"}))
            spoiled_ids = {it["id"] for it in newly_spoiled}
            affected = [
                c for c in self.customers
                if c["state"] == "waiting" and c.get("order_status") == "reserved"
                and any(rid in spoiled_ids for rid in c["reserved"])
            ]
            affected.sort(key=lambda c: (c.get("order_tick", 0), id_key(c["table_id"]), id_key(c["id"])))
            for c in affected:
                c["reserved"] = []
                picked = self._pick_reserve_ids(c["dish_id"])
                if picked is not None:
                    c["reserved"] = picked
                else:
                    c["order_status"] = "unfulfillable"

        # 3. Xét món chín theo id bếp
        for s in sort_by_id(self.stoves):
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"] = "ready"
                s["ready_ticks"] = 0
                events.append(("dish_ready", {
                    "stove_id": s["id"],
                    "order_id": s["order_id"],
                    "dish_id": s["dish"],
                }))

        # 4. Di chuyển và tối đa một tương tác
        self._move(inp)
        if inp.pressed("interact"):
            self._handle_interact(events)

        # 5. Thanh toán, kiên nhẫn / đóng ca
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
            self.hand = None
            for s in self.stoves:
                s["state"] = "idle"
                s["dish"] = None
                s["order_id"] = None
                s["base_price"] = None
                s["cook_ticks_left"] = 0
                s["ready_ticks"] = 0
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

        # 6. Nếu còn giờ: khách mới theo lịch
        if self.random_customers and self.time_left_ticks > 0:
            self._maybe_spawn_customer(events)

        return events

    # --- tiện ích -------------------------------------------------------------
    def _reserved_id_set(self) -> set:
        out = set()
        for c in self.customers:
            for rid in c.get("reserved", ()):
                out.add(rid)
        return out

    def _pick_reserve_ids(self, dish_id: str):
        """Chọn cá thể khả dụng chưa ươn tươi nhất (hòa theo id) cho từng loại trong công thức."""
        recipe = self.menu[dish_id]["recipe"]
        taken = self._reserved_id_set()
        avail_by_kind = {}
        for it in self.stock:
            if it["id"] in taken or it["fresh_frac"] < self.spoiled_below:
                continue
            avail_by_kind.setdefault(it["kind"], []).append(it)

        picked = []
        for kind in sorted(recipe):
            qty = recipe[kind]
            pool = avail_by_kind.get(kind, [])
            if len(pool) < qty:
                return None
            pool.sort(key=lambda x: (-x["fresh_frac"], id_key(x["id"])))
            for it in pool[:qty]:
                picked.append(it["id"])
        return sorted(picked, key=id_key)

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
                res_set = set(c["reserved"])
                used_items = [it for it in self.stock if it["id"] in res_set]
                self.stock = [it for it in self.stock if it["id"] not in res_set]

                avg_fresh = sum(it["fresh_frac"] for it in used_items) / Fraction(len(used_items))
                base_price = math.floor(Fraction(int(dish_cfg["price"])) * avg_fresh / Fraction(100))

                used_sorted = sorted(used_items, key=lambda x: (x["kind"], id_key(x["id"])))
                c["reserved"] = []
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
                    "items": [item_public(it) for it in used_sorted],
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

        dishes_eligible = []
        for dish_id in sorted(self.allowed_dishes):
            if self._pick_reserve_ids(dish_id) is not None:
                dishes_eligible.append(dish_id)

        if not dishes_eligible:
            events.append(("no_dish", {}))
            return

        dish_id = self.rng.get("customer").choice(dishes_eligible)
        picked = self._pick_reserve_ids(dish_id)
        c_id = self.ids.new("C")
        cust = {
            "id": c_id,
            "table_id": tb["id"],
            "dish_id": dish_id,
            "order_tick": self.phase_tick,
            "state": "waiting",
            "order_status": "reserved",
            "patience_ticks_left": int(round(self.t["patience_s"] * TICK)),
            "eat_ticks_left": 0,
            "reserved": picked,
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
