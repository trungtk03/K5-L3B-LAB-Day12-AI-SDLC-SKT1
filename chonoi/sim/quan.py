"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

========================================================================================
HƯỚNG DẪN DÀNH CHO NHÓM TRƯỞNG (trungtk03):
Module này chia thành 2 lát chính theo PRD-0 mục F ("Quán"):
  - LÁT 3: Vòng đời khách hàng, kiểm tra nguyên liệu, giữ chỗ (reserved), kiên nhẫn, customer_left, no_dish.
  - LÁT 4: Bếp nấu (cook_started, dish_ready), bưng món (dish_picked), phục vụ (served), thanh toán (paid), boa, uy tín, đóng ca (quan_end).

Tìm các thẻ [PHẦN VIỆC CẦN LÀM: ...] bên dưới để tự hoàn thiện logic.
========================================================================================
"""

import math
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
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # Kho: nạp từ file --inventory HOẶC scenario.stock
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.phase_tick = scenario.get("phase_tick", 0)
        self.reputation = float(scenario.get("reputation", t["reputation_initial"]))
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        
        # Khách hàng từ scenario:
        self.customers = [dict(c, reserved=c.get("reserved", {})) for c in scenario.get("customers", [])]
        for e in self.customers:
            ids.reserve(e["id"])
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
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # ----------------------------------------------------------------------------------
        # [PHẦN VIỆC CẦN LÀM - LÁT 4: BƯỚC 1 - CẬP NHẬT BẾP & TIMER]
        # 1. Tăng ready_ticks cho các món đã ở trạng thái "ready" từ đầu bước.
        # 2. Giảm cook_ticks_left cho bếp đang "cooking". Khi cook_ticks_left == 0:
        #    - Chuyển stove state sang "ready", đặt ready_ticks = 0.
        #    - Phát sinh event: ("dish_ready", {"stove_id": s["id"], "order_id": s["order_id"], "dish_id": s["dish"]})
        # 3. Giảm eat_ticks_left cho khách đang "eating".
        # 4. Giảm patience_ticks_left cho khách đang "waiting".
        # ----------------------------------------------------------------------------------

        # Di chuyển người chơi và chặn biên
        self._move(inp)

        # ----------------------------------------------------------------------------------
        # [PHẦN VIỆC CẦN LÀM - LÁT 4: BƯỚC 2 - TƯƠNG TÁC (INTERACT) TẠI BẾP HOẶC BÀN]
        # if inp.pressed("interact"):
        #   - Tìm đối tượng trong interact_radius (1.5m).
        #   - Tiêu chí ưu tiên: khoảng cách nhỏ nhất -> nếu bằng nhau thì Bếp trước Bàn -> nếu cùng loại thì id nhỏ hơn.
        #   - Tương tác Bếp:
        #       + Nếu Bếp idle: Tìm đơn reserved cũ nhất (order_tick nhỏ nhất -> id bàn nhỏ nhất).
        #         Tiêu hao nguyên liệu giữ trong self.stock, đặt state="cooking", chốt base_price.
        #         Phát sinh event: ("cook_started", {"stove_id": s["id"], "order_id": order_id, "dish_id": dish,
        #                                           "items": sorted(recipe), "base_price": base_price})
        #       + Nếu Bếp ready: Nếu tay người chơi đang trống (self.hand is None):
        #         Nhấc món lên tay: self.hand = {"order_id": ..., "dish_id": ..., "base_price": ...}
        #         Bếp trở về "idle".
        #         Phát sinh event: ("dish_picked", {"stove_id": s["id"], "order_id": order_id, "dish_id": dish})
        #   - Tương tác Bàn:
        #       + Nếu trên tay có món khớp order_id của khách đang ngồi bàn:
        #         Tính tip: Nếu (patience_ticks_left / (patience_s * 60)) >= tip_min_patience_ratio (0.5):
        #                   tip = math.floor(base_price * tip_rate), ngược lại tip = 0.
        #         Chuyển khách sang state="eating", order_status="served", đặt eat_ticks_left = eat_s * 60.
        #         Làm trống tay: self.hand = None.
        #         Phát sinh event: ("served", {"order_id": c["id"], "table_id": tb["id"], "dish_id": dish_id,
        #                                     "patience_ticks_left": c["patience_ticks_left"], "base_price": base_price, "tip": tip})
        # ----------------------------------------------------------------------------------

        # ----------------------------------------------------------------------------------
        # [PHẦN VIỆC CẦN LÀM - LÁT 3 & LÁT 4: BƯỚC 3 - KHÁCH ĂN XONG HOẶC HẾT KIÊN NHẪN]
        # Duyệt danh sách khách theo thứ tự id bàn:
        #   - Khách eating có eat_ticks_left == 0:
        #       + Thu tiền: amount = base_price + tip. Cộng vào self.money, self.earned, self.shift_earned.
        #       + Nếu tip > 0: cộng uy tín (self.reputation += tip_reputation), kẹp [min, max].
        #       + Phát sinh event: ("paid", {"order_id": c["id"], "table_id": c["table_id"], "base_price": c["base_price"],
        #                                   "tip": c["tip"], "amount": amount, "reason": "finished_eating"})
        #       + Khách rời quán, xóa khỏi self.customers.
        #   - Nếu ca còn giờ (time_left_ticks > 0) và khách waiting có patience_ticks_left == 0:
        #       + Trừ uy tín: self.reputation = max(reputation_min, self.reputation + left_reputation_delta).
        #       + Phát sinh event: ("customer_left", {"order_id": c["id"], "table_id": c["table_id"],
        #                                            "reason": "patience", "reputation": self.reputation})
        #       + Nhả nguyên liệu giữ chỗ (c["reserved"]).
        #       + Xóa khách khỏi self.customers.
        # ----------------------------------------------------------------------------------

        # ----------------------------------------------------------------------------------
        # [PHẦN VIỆC CẦN LÀM - LÁT 3: BƯỚC 4 - KHÁCH MỚI THEO LỊCH]
        # Nếu ca còn giờ (time_left_ticks > 0):
        #   - Kiểm tra nếu phase_tick == first_customer_tick (120) hoặc sau đó mỗi customer_interval_s * 60 ticks:
        #       + Tìm bàn trống có id nhỏ nhất (chưa có khách ngồi). Nếu không có bàn trống: bỏ qua.
        #       + Tính nguyên liệu khả dụng = self.stock - tổng nguyên liệu đang được khách khác giữ chỗ.
        #       + Xét 3 món trong menu:
        #           Món nào đủ nguyên liệu khả dụng?
        #       + Nếu KHÔNG có món nào đủ:
        #           Phát sinh event: ("no_dish", {})
        #       + Nếu có ít nhất 1 món đủ:
        #           Chọn món ngẫu nhiên đều bằng: dish_id = self.rng.get("customer").choice(dishes_eligible)
        #           Cấp id khách: c_id = self.ids.new("C")
        #           Tạo khách mới: order_id=c_id, table_id=bàn_trống, dish_id=dish_id,
        #                          order_tick=self.phase_tick, state="waiting",
        #                          patience_ticks_left=patience_s * 60, reserved=recipe_dict...
        #           Phát sinh event: ("customer_arrived", {"order_id": c_id, "table_id": bàn_trống["id"], "dish_id": dish_id})
        # ----------------------------------------------------------------------------------

        # ----------------------------------------------------------------------------------
        # [PHẦN VIỆC CẦN LÀM - LÁT 4: BƯỚC 5 - KẾT THÚC CA (QUAN_END)]
        # Khi self.time_left_ticks <= 0:
        #   - Khách đang ăn: trả tiền ngay (reason="closing"), phát "paid".
        #   - Khách đang chờ: rời bàn (reason="closing"), phát "customer_left" (không trừ uy tín).
        #   - Dọn dẹp và phát sinh event: ("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
        #                                              "shift_earned": self.shift_earned, "reputation": self.reputation})
        # ----------------------------------------------------------------------------------
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

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
