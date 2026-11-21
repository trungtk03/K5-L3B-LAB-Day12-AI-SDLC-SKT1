"""Bộ kiểm thử Phase 2 cho Vòng Ngày (--mode day), Shop nâng cấp, Pause và hiệu năng (Contract v1.1)."""

import json
import os
import time
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


class TestDayShopPauseP2(unittest.TestCase):
    def test_p2_day_01_tick_zero_events_and_plan(self):
        """--mode day tick 0: snapshot phase=gather, day=1, phát day_start -> day_plan -> phase_start tại tick 0."""
        with Workdir() as w:
            code, err = run_headless("--mode", "day", "--seed", "1", "--ticks", "0",
                                     "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
            s0 = snapshots(rows)[0]
            self.assertEqual(s0["mode"], "day")
            self.assertEqual(s0["phase"], "gather")
            self.assertEqual(s0["day"], 1)
            self.assertEqual(s0["phase_tick"], 0)
            self.assertEqual(s0["day_plan"]["dishes"], {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3})
            self.assertEqual(s0["day_plan"]["ingredients"], {"bong_sung": 6, "ca_loc": 3})
            self.assertEqual(s0["upgrades"], {})
            self.assertEqual(s0["active_upgrades"], {})

            evs = events(rows)
            self.assertEqual([(e["tick"], e["day"], e["phase"], e["name"]) for e in evs], [
                (0, 1, "gather", "day_start"),
                (0, 1, "gather", "day_plan"),
                (0, 1, "gather", "phase_start"),
            ])
            self.assertEqual(rows[-1]["days_completed"], 0)

    def test_p2_day_02_pause_freezes_sim_and_shop_timers(self):
        """Pause ở gather và shop: tick tăng, sim_tick/phase_tick/timer đứng yên, bỏ qua hành động/buy; resumed chạy ngay."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "day": {"money": 300, "earned": 300},
                "gather": {"hold": ["ca_loc"], "random_fish": False, "monsters": []},
                "quan": {"time_left_ticks": 2, "random_customers": False},
            })
            # Tick 0: interact cập bến -> chuyển sang quan (tick 1)
            # Tick 1..2: quan chạy 2 tick -> hết ca -> chuyển sang shop (tick 3)
            # Tick 3: pause=True (vào pause tại tick 4, sim_tick đứng yên)
            # Tick 4: buy='oxygen', shop_done=True bị bỏ qua vì đang pause!
            # Tick 5: pause=False (nhả nút)
            # Tick 6: pause=True (cạnh lên -> resumed + chạy gameplay ngay bước này, buy='oxygen' hoạt động!)
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 3, "pause": True},
                {"tick": 4, "buy": "oxygen", "shop_done": True},
                {"tick": 5, "pause": False, "shop_done": False},
                {"tick": 6, "pause": True, "buy": "oxygen"},
                {"tick": 7, "pause": False, "shop_done": True},
            ))
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "20",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1",
                                     "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
            snaps = {s["tick"]: s for s in snapshots(rows)}

            self.assertEqual(snaps[4]["state"], "paused")
            self.assertEqual(snaps[4]["sim_tick"], 3)
            self.assertEqual(snaps[5]["sim_tick"], 3)  # đứng yên trong pause
            self.assertEqual(snaps[5]["time_left_ticks"], snaps[3]["time_left_ticks"])  # timer shop đứng yên
            self.assertEqual(snaps[5]["money"], 300)  # buy trong pause bị bỏ qua

            # Tick 7 (frame tick 6): resumed + chạy buy='oxygen' ngay trong bước đó
            self.assertEqual(events(rows, "paused")[0]["tick"], 4)
            self.assertEqual(events(rows, "resumed")[0]["tick"], 7)
            bought = events(rows, "bought")
            self.assertEqual(len(bought), 1)
            self.assertEqual(bought[0]["tick"], 7)
            self.assertEqual(bought[0]["data"], {"upgrade": "oxygen", "level": 1, "price": 200, "money": 100})
            self.assertEqual(snaps[7]["upgrades"], {"oxygen": 1})
            self.assertEqual(snaps[7]["active_upgrades"], {})  # chỉ áp dụng từ Ngày kế!
            self.assertEqual(rows[-1]["money"], 100)
            self.assertEqual(rows[-1]["earned"], 300)  # earned giữ nguyên không giảm
            self.assertEqual(rows[-1]["score"], 600)   # 300 + 100 * floor(3.0)
            self.assertEqual(rows[-1]["days_completed"], 1)
            self.assertEqual(rows[-1]["reason"], "days_complete")

    def test_p2_day_03_plan_filters_evening_menu_and_shop_errors(self):
        """Trong day, quán chỉ phục vụ món thuộc day_plan; shop phát buy_failed cho unknown/funds/max_level."""
        with Workdir() as w:
            # Ngày 1 kế hoạch chỉ có ca_loc_nuong_trui & goi_bong_sung.
            # Mang về ca_keo ×2 (đủ nấu ca_keo_nuong nhưng KHÔNG thuộc kế hoạch D1) -> quán phải phát no_dish!
            sc = write_json(w.path("sc.json"), {
                "day": {"money": 650, "earned": 650},
                "gather": {"hold": ["ca_keo", "ca_keo"], "random_fish": False, "monsters": []},
                "quan": {"time_left_ticks": 130},
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},       # tick 1: gather_end -> quan
                {"tick": 1, "interact": False},
                # tick 131: quan_end -> shop (phase_tick 0)
                {"tick": 132, "buy": "oxygen"},      # lv1: -200 -> 450
                {"tick": 133, "buy": "oxygen"},      # lv2: -400 -> 50
                {"tick": 134, "buy": "oxygen"},      # max_level
                {"tick": 135, "buy": "hp"},          # funds (cần 250, còn 50)
                {"tick": 136, "buy": "unknown_item"},# unknown
                {"tick": 137, "shop_done": True},
            ))
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "200",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
            self.assertEqual(len(events(rows, "no_dish")), 1)
            self.assertEqual(len(events(rows, "customer_arrived")), 0)
            bf = events(rows, "buy_failed")
            self.assertEqual([e["data"] for e in bf], [
                {"action": "oxygen", "reason": "max_level"},
                {"action": "hp", "reason": "funds"},
                {"action": "unknown_item", "reason": "unknown"},
            ])

    def test_p2_day_04_multi_day_upgrades_effective_next_day_and_m2_on_day_3(self):
        """Chạy 3 Ngày: mua oxygen lv1 & hp lv1 ở Ngày 1 -> Ngày 2 có 45s oxy & 4 Máu; Ngày 3 có cả M1 & M2."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "day": {"money": 500, "earned": 500},
                "gather": {"random_fish": False},
                "quan": {"time_left_ticks": 1, "random_customers": False},
            })
            # Ngày 1: tick 0 dock (tick 1 -> quan), tick 1 quan_end (tick 2 -> shop),
            #         tick 2 buy oxygen (-200), tick 3 buy hp (-250) + shop_done (tick 4 -> Day 2 gather!)
            # Ngày 2: tick 4 dock (tick 5 -> quan), tick 5 quan_end (tick 6 -> shop),
            #         tick 6 shop_done (tick 7 -> Day 3 gather!)
            # Ngày 3: tick 7 dock (tick 8 -> quan), tick 8 quan_end (tick 9 -> shop),
            #         tick 9 shop_done (tick 10 -> days_complete!)
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 2, "buy": "oxygen"},
                {"tick": 3, "buy": "hp", "shop_done": True},
                {"tick": 4, "shop_done": False, "interact": True},
                {"tick": 5, "interact": False},
                {"tick": 6, "shop_done": True},
                {"tick": 7, "shop_done": False, "interact": True},
                {"tick": 8, "interact": False},
                {"tick": 9, "shop_done": True},
            ))
            code, err = run_headless("--mode", "day", "--days", "3", "--seed", "1", "--ticks", "30",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1",
                                     "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
            snaps = {s["tick"]: s for s in snapshots(rows)}

            # Ngày 1 (tick 0): 30s oxy (1800), 3 Máu, 1 Cá Sấu (M1)
            self.assertEqual(snaps[0]["player"]["oxygen_max_ticks"], 1800)
            self.assertEqual(snaps[0]["player"]["hp_max"], 3)
            self.assertEqual([m["id"] for m in snaps[0]["monsters"]], ["M1"])

            # Ngày 2 (tick 4): active_upgrades đã áp dụng -> 45s oxy (2700), 4 Máu, vẫn chỉ có M1
            self.assertEqual(snaps[4]["day"], 2)
            self.assertEqual(snaps[4]["phase"], "gather")
            self.assertEqual(snaps[4]["active_upgrades"], {"hp": 1, "oxygen": 1})
            self.assertEqual(snaps[4]["player"]["oxygen_max_ticks"], 2700)
            self.assertEqual(snaps[4]["player"]["hp_max"], 4)
            self.assertEqual([m["id"] for m in snaps[4]["monsters"]], ["M1"])

            # Ngày 3 (tick 7): M1 và M2 cùng xuất hiện!
            self.assertEqual(snaps[7]["day"], 3)
            self.assertEqual(snaps[7]["phase"], "gather")
            self.assertEqual([m["id"] for m in snaps[7]["monsters"]], ["M1", "M2"])

            end = rows[-1]
            self.assertEqual(end["days_completed"], 3)
            self.assertEqual(end["reason"], "days_complete")
            self.assertEqual(end["money"], 50)
            self.assertEqual(end["earned"], 500)

    def test_p2_day_05_faint_opens_empty_evening_and_shop_timeout(self):
        """Ngất ở gather vẫn mở quan với kho rỗng; Shop hết 600 tick tự đóng phát shop_end(time)."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [60, 24], "hp": 1},
                    "hold": ["ca_loc"],
                    "random_fish": False,
                },
                "quan": {"time_left_ticks": 1, "random_customers": False},
            })
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "700",
                                     "--scenario", sc, "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
            ge = events(rows, "gather_end")[0]
            self.assertEqual(ge["data"]["reason"], "fainted")
            self.assertEqual(ge["data"]["inventory"], {"items": {}})
            # Quan mở ngay cùng tick 1 với stock rỗng
            ps_q = [e for e in events(rows, "phase_start") if e["phase"] == "quan"]
            self.assertEqual(len(ps_q), 1)
            self.assertEqual(ps_q[0]["tick"], 1)
            # Shop tự đóng sau 600 tick với reason="time"
            se = events(rows, "shop_end")[0]
            self.assertEqual(se["data"], {"reason": "time"})
            self.assertEqual(rows[-1]["days_completed"], 1)
            self.assertEqual(rows[-1]["reason"], "days_complete")

    def test_p2_day_06_scenario_and_cli_contradictions_exit_2(self):
        """Các lỗi CLI / mâu thuẫn scenario trong mode day trả mã 2 trước khi ghi file."""
        with Workdir() as w:
            out = w.path("out.jsonl")
            # --days sai mode / ngoài [1, 5]
            self.assertEqual(run_headless("--mode", "gather", "--days", "1", "--seed", "1", "--ticks", "0", "--out", out)[0], 2)
            self.assertEqual(run_headless("--mode", "day", "--days", "6", "--seed", "1", "--ticks", "0", "--out", out)[0], 2)
            self.assertFalse(os.path.exists(out))

            bad_scenarios = [
                {"quan": {"stock": {"ca_loc": 1}}},          # cấm quan.stock trong day
                {"quan": {"reputation": 4.0}},               # cấm quan.reputation trong day
                {"day": {"money": 100}},                     # thiếu earned khi money > 0
                {"day": {"money": 200, "earned": 100}},      # money > earned
                {"day": {"day_plan": [{"day": 1, "dishes": {"ca_loc_nuong_trui": 1}, "ingredients": {"ca_loc": 99}}]}},
            ]
            for i, sc_obj in enumerate(bad_scenarios):
                sc = write_json(w.path(f"bad_{i}.json"), sc_obj)
                code, _ = run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, f"bad scenario #{i} phải trả mã 2")
                self.assertFalse(os.path.exists(out))

    def test_p2_day_07_determinism_and_full_day_performance(self):
        """Một Ngày đầy đủ không pause (<= 22.200 tick) chạy nhanh hơn 20s và tất định từng byte."""
        with Workdir() as w:
            t0 = time.perf_counter()
            for i in (1, 2):
                code, err = run_headless("--mode", "day", "--days", "1", "--seed", "11", "--ticks", "22200",
                                         "--snapshot-every", "60", "--out", w.path(f"d{i}.jsonl"))
                self.assertEqual(code, 0, err)
            elapsed = (time.perf_counter() - t0) / 2.0
            self.assertLess(elapsed, 20.0, f"một Ngày chạy mất {elapsed:.2f}s (> 20s)")
            with open(w.path("d1.jsonl"), "rb") as a, open(w.path("d2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            rows = read_jsonl(w.path("d1.jsonl"))
            self.assertEqual(rows[-1]["days_completed"], 1)
            self.assertEqual(rows[-1]["reason"], "days_complete")


if __name__ == "__main__":
    unittest.main()
