"""Cửa hàng cuối ngày (`shop`, Contract v1.1).

Mua nâng cấp theo dữ liệu (`oxygen`, `hp`), trừ `money`, giữ `earned` và `score`.
Cấp vừa mua cập nhật ngay vào `upgrades`, có hiệu lực từ Ngày kế tiếp (`active_upgrades`).
Xử lý một `buy` trước cạnh `shop_done`, kể cả ở bước cuối (`max_ticks = 600`).
"""


class ShopSim:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, stock, money, earned, reputation, upgrades):
        self.cfg = tuning["shop"]
        self.stock = {k: v for k, v in sorted(stock.items()) if v > 0}
        self.money = int(money)
        self.earned = int(earned)
        self.reputation = float(reputation)
        self.upgrades = {k: int(v) for k, v in sorted(upgrades.items()) if int(v) > 0}
        self.time_left_ticks = int(self.cfg["max_ticks"])
        self.phase_tick = 0
        self.done = False
        self.reason = None

    def snapshot(self) -> dict:
        return {
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
        }

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Xử lý một lệnh buy trước cạnh shop_done (kể cả bước cuối)
        if inp.buy:
            action = inp.buy
            up_map = self.cfg["upgrades"]
            if action not in up_map:
                events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            else:
                tiers = up_map[action]
                cur = self.upgrades.get(action, 0)
                nxt = next((t for t in tiers if t["level"] == cur + 1), None)
                if nxt is None:
                    events.append(("buy_failed", {"action": action, "reason": "max_level"}))
                elif self.money < int(nxt["price"]):
                    events.append(("buy_failed", {"action": action, "reason": "funds"}))
                else:
                    price = int(nxt["price"])
                    self.money -= price
                    self.upgrades[action] = int(nxt["level"])
                    events.append(("bought", {
                        "upgrade": action,
                        "level": int(nxt["level"]),
                        "price": price,
                        "money": self.money,
                    }))

        # 2. Đóng bằng nút ở bước cuối phát shop_end(done); tự hết giờ phát shop_end(time)
        if inp.pressed("shop_done"):
            self.done = True
            self.reason = "done"
            events.append(("shop_end", {"reason": "done"}))
        elif self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("shop_end", {"reason": "time"}))

        return events
