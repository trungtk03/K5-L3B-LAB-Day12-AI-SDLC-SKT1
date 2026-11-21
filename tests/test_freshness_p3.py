"""Bộ kiểm thử Phase 3 — Độ tươi & Kho cá thể (TICKET-03, Test Contract v1.2).

Kiểm chứng:
  - Ngưỡng ươn chính xác 30 -> < 30 ở cả gather và quan (phát spoiled đúng 1 lần theo thứ tự id).
  - Bàn giao file kho cá thể (smoke TICKET-03) và từ chối kho đếm cũ (mã 2).
  - Cấp id I1, I2, ... tăng liên tục xuyên pha & xuyên Ngày; Ngày 2+ cấp id mới cho gather.hold mẫu.
  - Giữ chỗ theo id cá thể tươi nhất (hòa theo id), thử giữ lại đúng 1 lần khi hàng giữ vừa ươn, chuyển unfulfillable nếu thiếu.
  - Chốt giá base_price = floor(giá niêm yết * avg_fresh / 100), boa trên giá đã chốt, cook_started.data.items sắp theo (kind, id).
  - Pause dừng hao tươi ở cả gather & quan; Shop không hao tươi kho dư.
  - Giao đúng tick kiên nhẫn = 0 vẫn hợp lệ; giao đúng tick kết thúc ca được trả ngay (closing).
"""

import json
import unittest

from helpers import Workdir, close, events, frames, read_jsonl, run_headless, snapshots, write_json


class TestFreshnessP3(unittest.TestCase):
    def test_p3_01_gather_threshold_30_spoils_on_tick_1_in_id_order(self):
        """Mẫu kiểm ngưỡng TICKET-03: fresh=30 ở gather ươn ngay tick 1; nhiều cá thể cùng vượt ngưỡng phát theo id."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [
                        {"id": "I10", "kind": "ca_loc", "fresh": 30},
                        {"id": "I2", "kind": "ca_linh", "fresh": 30},
                        {"id": "I1", "kind": "bong_sung", "fresh": 29.5},  # đã ươn sẵn -> không phát spoiled lại
                    ],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "3",
                                     "--scenario", sc, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            sp = events(rows, "spoiled")
            self.assertEqual(sp, [
                {"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
                 "data": {"item_id": "I2", "kind": "ca_linh", "location": "hold"}},
                {"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
                 "data": {"item_id": "I10", "kind": "ca_loc", "location": "hold"}},
            ])

    def test_p3_02_smoke_file_handoff_exact_freshness_and_threshold(self):
        """Smoke bàn giao file TICKET-03: gather fresh=100 cập bến frame 0 -> quan --inventory --ticks 0 khớp id/kind/fresh."""
        with Workdir() as w:
            inv = w.path("inv.json")
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp,
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(len(saved["items"]), 1)
            self.assertEqual(saved["items"][0]["id"], "I1")
            self.assertEqual(saved["items"][0]["kind"], "ca_linh")
            self.assertAlmostEqual(saved["items"][0]["fresh"], 100 - 1 / 120, places=6)

            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", inv, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            q_stock = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
            self.assertEqual(len(q_stock), 1)
            self.assertEqual(q_stock[0]["id"], "I1")
            self.assertEqual(q_stock[0]["kind"], "ca_linh")
            self.assertTrue(close(q_stock[0]["fresh"], saved["items"][0]["fresh"], 0.01))

    def test_p3_03_quan_spoiled_re_reserve_once_or_unfulfillable(self):
        """Khi cá thể đang giữ bị ươn: phát spoiled trước, nhả hết phần giữ & thử giữ lại 1 lần theo (order_tick, table_id)."""
        with Workdir() as w:
            # C1 (order_tick=1, T1) giữ [I1(30), I2(80)] cho goi_bong_sung (cần 2 bong_sung)
            # C2 (order_tick=2, T2) giữ [I3(30)] cho ca_loc_nuong_trui (cần 1 ca_loc)
            # Kho còn I4 (bong_sung, 90) dự phòng -> C1 nhả [I1, I2] rồi giữ lại được [I2, I4]; C2 không còn ca_loc -> unfulfillable!
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "random_customers": False,
                    "stock": [
                        {"id": "I1", "kind": "bong_sung", "fresh": 30},
                        {"id": "I2", "kind": "bong_sung", "fresh": 80},
                        {"id": "I3", "kind": "ca_loc", "fresh": 30},
                        {"id": "I4", "kind": "bong_sung", "fresh": 90},
                    ],
                    "customers": [
                        {"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "order_tick": 1, "reserved": ["I1", "I2"]},
                        {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 2, "reserved": ["I3"]},
                    ],
                }
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            sp = events(rows, "spoiled")
            self.assertEqual([e["data"]["item_id"] for e in sp], ["I1", "I3"])
            self.assertTrue(all(e["tick"] == 1 and e["data"]["location"] == "stock" for e in sp))

            s1 = {s["tick"]: s for s in snapshots(rows)}[1]
            c_by_id = {c["id"]: c for c in s1["customers"]}
            self.assertEqual(c_by_id["C1"]["order_status"], "reserved")
            self.assertEqual(c_by_id["C1"]["reserved"], ["I2", "I4"])
            self.assertEqual(c_by_id["C2"]["order_status"], "unfulfillable")
            self.assertEqual(c_by_id["C2"]["reserved"], [])

    def test_p3_04_dynamic_price_by_avg_fresh_and_cook_items_sorted(self):
        """Giá chốt = floor(giá niêm yết * avg_fresh / 100); cook_started.items sắp theo (kind, id); boa áp trên giá đã chốt."""
        with Workdir() as w:
            # canh_chua_ca_loc (giá 90): ca_loc x1 + bong_dien_dien x1
            # Kho: I2 ca_loc fresh 60 + 1/240 (sau tick 1 còn đúng 60.0), I1 bong_dien_dien fresh 80 + 1/240 (sau tick 1 còn đúng 80.0)
            # avg_fresh = (60 + 80)/2 = 70.0 -> base_price = floor(90 * 70 / 100) = 63; tip = floor(63 * 0.2) = 12
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [2, 8]},
                    "random_customers": False,
                    "stock": [
                        {"id": "I2", "kind": "ca_loc", "fresh": 60 + 1 / 240},
                        {"id": "I1", "kind": "bong_dien_dien", "fresh": 80 + 1 / 240},
                        {"id": "I3", "kind": "ca_loc", "fresh": 50},  # kém tươi hơn -> không được chọn!
                    ],
                    "customers": [
                        {"id": "C1", "table_id": "T1", "dish_id": "canh_chua_ca_loc", "state": "waiting"},
                    ],
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            cs = events(rows, "cook_started")[0]["data"]
            self.assertEqual(cs["base_price"], 63)
            # Sắp theo (kind, id): bong_dien_dien (I1) trước ca_loc (I2)
            self.assertEqual([(it["kind"], it["id"]) for it in cs["items"]],
                             [("bong_dien_dien", "I1"), ("ca_loc", "I2")])

    def test_p3_05_pause_stops_freshness_decay_and_shop_no_decay(self):
        """Pause đóng băng hao tươi ở gather & quan; kho dư ở Shop không hao tươi."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 30}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            # Tick 0: pause=True (vào pause tại tick 1 -> KHÔNG hao tươi, KHÔNG phát spoiled)
            # Tick 1..4: đứng yên trong pause
            # Tick 5: pause=False; Tick 6: pause=True (resumed tại tick 7 -> hao tươi -> spoiled ở tick 7!)
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "pause": True},
                {"tick": 5, "pause": False},
                {"tick": 6, "pause": True},
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "10",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            sp = events(read_jsonl(w.path("g.jsonl")), "spoiled")
            self.assertEqual(len(sp), 1)
            self.assertEqual(sp[0]["tick"], 7)

            # Kiểm Shop không hao tươi kho dư
            sc_day = write_json(w.path("sc_day.json"), {
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 80}],
                    "random_fish": False,
                    "monsters": [],
                },
                "quan": {"time_left_ticks": 1, "random_customers": False},
            })
            inp_day = write_json(w.path("in_day.json"), frames(
                {"tick": 0, "interact": True},   # tick 1 -> quan
                {"tick": 1, "interact": False},  # tick 2 -> shop
                {"tick": 102, "shop_done": True},  # chạy 100 tick trong Shop
            ))
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "120",
                                     "--scenario", sc_day, "--inputs", inp_day, "--snapshot-every", "1",
                                     "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            snaps = {s["tick"]: s for s in snapshots(read_jsonl(w.path("d.jsonl")))}
            self.assertEqual(snaps[2]["phase"], "shop")
            self.assertEqual(snaps[100]["phase"], "shop")
            self.assertEqual(snaps[2]["stock"][0]["fresh"], snaps[100]["stock"][0]["fresh"])

    def test_p3_06_id_monotonic_across_days_and_day2_reallocates_template_hold(self):
        """Trong day: Ngày 1 giữ id mẫu gather.hold, Ngày 2+ cấp id mới nối tiếp (I1.. -> I3..)."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [
                        {"id": "I1", "kind": "ca_loc", "fresh": 95},
                        {"id": "I2", "kind": "bong_sung", "fresh": 90},
                    ],
                    "random_fish": False,
                    "monsters": [],
                },
                "quan": {"time_left_ticks": 1, "random_customers": False},
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 2, "shop_done": True},
                {"tick": 3, "shop_done": False, "interact": True},
                {"tick": 4, "interact": False},
                {"tick": 5, "shop_done": True},
            ))
            code, err = run_headless("--mode", "day", "--days", "2", "--seed", "1", "--ticks", "20",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1",
                                     "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            snaps = {s["tick"]: s for s in snapshots(read_jsonl(w.path("d.jsonl")))}
            self.assertEqual([it["id"] for it in snaps[0]["hold"]], ["I1", "I2"])
            self.assertEqual(snaps[3]["day"], 2)
            self.assertEqual(snaps[3]["phase"], "gather")
            self.assertEqual([it["id"] for it in snaps[3]["hold"]], ["I3", "I4"])
            self.assertEqual([it["fresh"] for it in snaps[3]["hold"]], [95, 90])

    def test_p3_07_serve_on_exact_patience_zero_and_closing_tick(self):
        """Giao đúng tick kiên nhẫn chạm 0 vẫn hợp lệ; giao đúng tick hết ca được trả tiền ngay (closing)."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [9, 2]},
                    "time_left_ticks": 1,
                    "random_customers": False,
                    "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 55},
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "state": "waiting",
                        "order_status": "assigned",
                        "patience_ticks_left": 1,  # giảm về 0 đúng tick 1, đồng thời time_left_ticks giảm về 0!
                    }],
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            self.assertEqual(len(events(rows, "served")), 1)
            self.assertEqual(events(rows, "served")[0]["data"]["patience_ticks_left"], 0)
            pd = events(rows, "paid")
            self.assertEqual(len(pd), 1)
            self.assertEqual(pd[0]["data"]["reason"], "closing")
            self.assertEqual(pd[0]["data"]["amount"], 55)
            self.assertEqual(rows[-1]["money"], 55)


if __name__ == "__main__":
    unittest.main()
