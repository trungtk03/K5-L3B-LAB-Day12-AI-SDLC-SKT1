"""Bộ kiểm thử cho Lát 3 & Lát 4 (Quán) và liên thông E2E 2 tiến trình (cập nhật schema cá thể Contract v1.2).

Chạy:
    PYTHONPATH=tests:. python3 -m unittest tests/test_quan_lat3_lat4.py -v
"""

import json
import os
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim
from helpers import Workdir, close, events, frames, items_v12, read_jsonl, run_headless, snapshots, write_json


class TestQuanLat3Lat4(unittest.TestCase):
    def test_quan_00_starter_fixture(self):
        """Quán khởi động bình thường với 2 bếp (B1-B2) và 4 bàn (T1-T4) theo Contract v1.1/v1.2."""
        with Workdir() as w:
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "10",
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            s = snapshots(rows)[0]
            self.assertEqual(len(s["stoves"]), 2)
            self.assertEqual(len(s["tables"]), 4)

    # ---- LÁT 3: Khách theo lịch, chọn món, giữ chỗ theo id, kiên nhẫn, no_dish ----

    def test_quan_lat3_01_no_dish_when_stock_empty(self):
        """Kho rỗng -> tick 120 và tick 1020 phát no_dish, không có khách."""
        with Workdir() as w:
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1030",
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            nd = events(rows, "no_dish")
            self.assertEqual([e["tick"] for e in nd], [120, 1020])
            self.assertEqual(len(events(rows, "customer_arrived")), 0)

    def test_quan_lat3_02_customer_arrived_and_reserves_ingredients(self):
        """Kho đủ 1 món -> tick 120 sinh khách C1 tại T1 và giữ chỗ id cá thể ['I1'] (chưa trừ kho)."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"stock": items_v12("ca_loc")}})
            code, err = run_headless("--mode", "quan", "--seed", "7", "--ticks", "130",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            arr = events(rows, "customer_arrived")
            self.assertEqual(len(arr), 1)
            self.assertEqual(arr[0]["tick"], 120)
            self.assertEqual(arr[0]["data"], {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})

            snaps = {s["tick"]: s for s in snapshots(rows)}
            s120 = snaps[120]
            self.assertEqual(len(s120["stock"]), 1)
            self.assertEqual(s120["stock"][0]["id"], "I1")
            self.assertEqual(len(s120["customers"]), 1)
            c = s120["customers"][0]
            self.assertEqual(c["id"], "C1")
            self.assertEqual(c["state"], "waiting")
            self.assertEqual(c["order_status"], "reserved")
            self.assertEqual(c["reserved"], ["I1"])
            self.assertEqual(c["patience_ticks_left"], 3600)

    def test_quan_lat3_03_deterministic_bytes_same_seed(self):
        """Cùng seed và cùng kho -> JSONL buổi tối giống hệt nhau từng byte."""
        with Workdir() as w:
            stock = items_v12("ca_loc", "ca_loc", "bong_sung", "bong_sung", "bong_sung", "bong_sung",
                              "ca_linh", "ca_linh", "ca_linh", "bong_dien_dien")
            sc = write_json(w.path("sc.json"), {"quan": {"stock": stock}})
            for i in (1, 2):
                code, err = run_headless("--mode", "quan", "--seed", "42", "--ticks", "300",
                                         "--scenario", sc, "--out", w.path(f"q{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("q1.jsonl"), "rb") as a, open(w.path("q2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())

    def test_quan_lat3_04_patience_expiry_reputation_and_release_reserve(self):
        """Khách hết kiên nhẫn: rời quán, trừ 0.5 uy tín (kẹp >= 0), nhả id giữ chỗ cho khách sau."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "stock": items_v12("ca_loc"),
                    "reputation": 0.3,
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "state": "waiting",
                        "patience_ticks_left": 10,
                    }],
                }
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "125",
                                     "--scenario", sc, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            left = events(rows, "customer_left")
            self.assertEqual(len(left), 1)
            self.assertEqual(left[0]["tick"], 10)
            self.assertEqual(left[0]["data"]["order_id"], "C1")
            self.assertEqual(left[0]["data"]["reason"], "patience")
            self.assertEqual(left[0]["data"]["reputation"], 0.0)

            arr = events(rows, "customer_arrived")
            self.assertEqual(len(arr), 1)
            self.assertEqual(arr[0]["tick"], 120)
            self.assertEqual(arr[0]["data"]["order_id"], "C2")
            self.assertEqual(arr[0]["data"]["dish_id"], "ca_loc_nuong_trui")

    def test_quan_lat3_05_random_customers_false(self):
        """random_customers=false tắt lịch sinh khách tự động."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"random_customers": False}})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "200",
                                     "--scenario", sc, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            self.assertEqual(len(events(rows, "no_dish")), 0)
            self.assertEqual(len(events(rows, "customer_arrived")), 0)

    # ---- LÁT 4: Bếp nấu (giá theo độ tươi v1.2), bưng món, phục vụ, boa, uy tín, kết ca ----

    def test_quan_lat4_01_full_cook_pick_serve_pay_with_tip(self):
        """Luồng đầy đủ (v1.2): hao 1 tick ở quán -> base_price = floor(60 * 99.99583 / 100) = 59, tip = floor(59*0.2) = 11."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [2, 8]},
                    "stock": items_v12("ca_loc"),
                    "random_customers": False,
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "state": "waiting",
                        "patience_ticks_left": 3600,
                    }],
                }
            })
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 363, "interact": True},
                {"tick": 364, "interact": False, "move": [1, -1]},
                {"tick": 496, "move": [0, 0], "interact": True},
                {"tick": 497, "interact": False},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1120",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1",
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            snaps = {s["tick"]: s for s in snapshots(rows)}

            cs = events(rows, "cook_started")
            self.assertEqual(len(cs), 1)
            self.assertEqual(cs[0]["tick"], 1)
            self.assertEqual(cs[0]["data"]["stove_id"], "B1")
            self.assertEqual(cs[0]["data"]["order_id"], "C1")
            self.assertEqual(cs[0]["data"]["dish_id"], "ca_loc_nuong_trui")
            self.assertEqual(len(cs[0]["data"]["items"]), 1)
            self.assertEqual(cs[0]["data"]["items"][0]["id"], "I1")
            self.assertEqual(cs[0]["data"]["base_price"], 59)  # floor(60 * (100 - 1/240) / 100)
            self.assertEqual(snaps[1]["stock"], [])
            self.assertEqual(snaps[1]["stoves"][0]["state"], "cooking")
            self.assertEqual(snaps[1]["stoves"][0]["cook_ticks_left"], 360)

            dr = events(rows, "dish_ready")
            self.assertEqual(len(dr), 1)
            self.assertEqual(dr[0]["tick"], 361)
            self.assertEqual(snaps[361]["stoves"][0]["state"], "ready")
            self.assertEqual(snaps[361]["stoves"][0]["ready_ticks"], 0)
            self.assertEqual(snaps[362]["stoves"][0]["ready_ticks"], 1)

            dp = events(rows, "dish_picked")
            self.assertEqual(len(dp), 1)
            self.assertEqual(dp[0]["tick"], 364)
            self.assertEqual(snaps[364]["hand"], {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 59})
            self.assertEqual(snaps[364]["stoves"][0]["state"], "idle")

            sv = events(rows, "served")
            self.assertEqual(len(sv), 1)
            self.assertEqual(sv[0]["tick"], 497)
            self.assertEqual(sv[0]["data"]["base_price"], 59)
            self.assertEqual(sv[0]["data"]["tip"], 11)  # floor(59 * 0.2)
            self.assertIsNone(snaps[497]["hand"])

            pd = events(rows, "paid")
            self.assertEqual(len(pd), 1)
            self.assertEqual(pd[0]["tick"], 1097)
            self.assertEqual(pd[0]["data"], {
                "order_id": "C1",
                "table_id": "T1",
                "base_price": 59,
                "tip": 11,
                "amount": 70,
                "reason": "finished_eating",
            })
            end = rows[-1]
            self.assertEqual(end["money"], 70)
            self.assertEqual(end["earned"], 70)
            self.assertEqual(end["reputation"], 3.2)
            self.assertEqual(end["score"], 370)  # 70 + 100 * floor(3.2)

    def test_quan_lat4_02_serve_low_patience_no_tip(self):
        """Phục vụ khi kiên nhẫn < 50%: tip = 0, không tăng uy tín."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "quan": {
                    "player": {"pos": [9, 2]},
                    "random_customers": False,
                    "hand": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40},
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "goi_bong_sung",
                        "state": "waiting",
                        "order_status": "assigned",
                        "patience_ticks_left": 1000,
                    }],
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "610",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            sv = events(rows, "served")[0]
            self.assertEqual(sv["data"]["tip"], 0)
            pd = events(rows, "paid")[0]
            self.assertEqual(pd["data"]["amount"], 40)
            self.assertEqual(rows[-1]["reputation"], 3.0)
            self.assertEqual(rows[-1]["score"], 340)

    def test_quan_lat4_03_closing_time_settles_eating_and_waiting(self):
        """Hết giờ ca: khách đang ăn trả tiền ngay (closing); khách đang chờ rời đi không trừ uy tín."""
        with Workdir() as w:
            sc1 = write_json(w.path("sc1.json"), {
                "quan": {
                    "time_left_ticks": 5,
                    "reputation": 4.9,
                    "random_customers": False,
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "lau_ca_linh_dien_dien",
                        "state": "eating",
                        "eat_ticks_left": 500,
                        "base_price": 120,
                        "tip": 24,
                    }],
                }
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "20",
                                     "--scenario", sc1, "--out", w.path("q1.jsonl"))
            self.assertEqual(code, 0, err)
            rows1 = read_jsonl(w.path("q1.jsonl"))
            pd = events(rows1, "paid")
            self.assertEqual(len(pd), 1)
            self.assertEqual(pd[0]["data"]["reason"], "closing")
            self.assertEqual(pd[0]["data"]["amount"], 144)
            qe1 = events(rows1, "quan_end")[0]
            self.assertEqual(qe1["data"], {
                "reason": "time",
                "money": 144,
                "earned": 144,
                "shift_earned": 144,
                "reputation": 5.0,
            })
            self.assertEqual(rows1[-1]["score"], 644)

            sc2 = write_json(w.path("sc2.json"), {
                "quan": {
                    "time_left_ticks": 5,
                    "reputation": 3.0,
                    "stock": items_v12("ca_loc"),
                    "random_customers": False,
                    "customers": [{
                        "id": "C1",
                        "table_id": "T1",
                        "dish_id": "ca_loc_nuong_trui",
                        "state": "waiting",
                        "patience_ticks_left": 500,
                    }],
                }
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "20",
                                     "--scenario", sc2, "--out", w.path("q2.jsonl"))
            self.assertEqual(code, 0, err)
            rows2 = read_jsonl(w.path("q2.jsonl"))
            cl = events(rows2, "customer_left")
            self.assertEqual(len(cl), 1)
            self.assertEqual(cl[0]["data"]["reason"], "closing")
            self.assertEqual(cl[0]["data"]["reputation"], 3.0)
            self.assertEqual(rows2[-1]["reputation"], 3.0)

    def test_quan_lat4_04_tie_breaking_stove_before_table_and_oldest_order(self):
        """Unit test ưu tiên: khi khoảng cách bằng nhau -> Bếp trước Bàn; chọn đơn reserved cũ nhất."""
        tuning = load_contract()["tuning"]
        tuning["quan"]["stoves"] = [{"id": "B1", "pos": [5, 5]}]
        tuning["quan"]["tables"] = [{"id": "T1", "pos": [6, 5]}, {"id": "T2", "pos": [12, 5]}]
        scenario = {
            "player": {"pos": [5.5, 5.0]},
            "stock": items_v12("ca_loc", "bong_sung", "bong_sung"),
            "random_customers": False,
            "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
            "customers": [
                {
                    "id": "C1",
                    "table_id": "T1",
                    "dish_id": "ca_loc_nuong_trui",
                    "state": "waiting",
                    "order_status": "assigned",
                    "order_tick": 10,
                },
                {
                    "id": "C2",
                    "table_id": "T2",
                    "dish_id": "goi_bong_sung",
                    "state": "waiting",
                    "order_status": "reserved",
                    "order_tick": 20,
                },
            ],
        }
        sim = QuanSim(tuning, scenario, Streams(1), IdAllocator())
        evs = sim.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        names = [name for name, _ in evs]
        self.assertIn("cook_started", names)
        self.assertNotIn("served", names)
        self.assertEqual(evs[0][1]["order_id"], "C2")

    def test_quan_scenario_contradictions_exit_2(self):
        """Các mâu thuẫn mức luật trong scenario phải thoát mã 2 trước khi ghi file đầu ra."""
        bad_blocks = [
            # Giữ chỗ vượt kho
            {
                "stock": [],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "waiting"}],
            },
            # Đơn assigned nhưng không có món trên bếp hay trên tay
            {
                "customers": [{
                    "id": "C1",
                    "table_id": "T1",
                    "dish_id": "ca_loc_nuong_trui",
                    "state": "waiting",
                    "order_status": "assigned",
                }],
            },
            # Khách eating thiếu base_price / tip
            {
                "customers": [{
                    "id": "C1",
                    "table_id": "T1",
                    "dish_id": "ca_loc_nuong_trui",
                    "state": "eating",
                    "eat_ticks_left": 100,
                }],
            },
            # Khách reserved trỏ tới cá thể đã ươn (fresh < 30)
            {
                "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 25}],
                "customers": [{
                    "id": "C1",
                    "table_id": "T1",
                    "dish_id": "ca_loc_nuong_trui",
                    "state": "waiting",
                    "reserved": ["I1"],
                }],
            },
        ]
        for idx, block in enumerate(bad_blocks):
            with Workdir() as w:
                sc = write_json(w.path("sc.json"), {"quan": block})
                out = w.path("out.jsonl")
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "5",
                                       "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, f"case #{idx} phải trả mã 2")
                self.assertFalse(os.path.exists(out), f"case #{idx} không được tạo file đầu ra")

    def test_e2e_two_process_gather_to_quan_full_cycle(self):
        """E2E 2 tiến trình (v1.2): bắt cá lóc + cập bến ghi kho cá thể -> quán đọc kho, nấu theo giá tươi, phục vụ, thu tiền."""
        with Workdir() as w:
            inv = w.path("inv.json")
            sc_g = write_json(w.path("sc_g.json"), {
                "gather": {
                    "player": {"pos": [4, 1.5]},
                    "fish": [{"id": "F1", "kind": "ca_loc", "pos": [4, 1.5], "heading_deg": 0}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            inp_g = write_json(w.path("in_g.json"), frames(
                {"tick": 0, "catch": True},
                {"tick": 1, "catch": False, "move": [-1, -1]},
                {"tick": 45, "move": [0, 0], "interact": True},
            ))
            code, err = run_headless("--mode", "gather", "--seed", "7", "--ticks", "60",
                                     "--scenario", sc_g, "--inputs", inp_g,
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(len(saved["items"]), 1)
            self.assertEqual(saved["items"][0]["id"], "I1")
            self.assertEqual(saved["items"][0]["kind"], "ca_loc")
            # Bắt ở tick 1 (fresh=100), hao 45 tick (tick 2..46): 100 - 45/120 = 99.625
            self.assertTrue(close(saved["items"][0]["fresh"], 99.625, 0.01), saved)

            inp_q = write_json(w.path("in_q.json"), frames(
                {"tick": 0, "move": [-1, 0.5]},
                {"tick": 100, "move": [0, 0]},
                {"tick": 121, "interact": True},
                {"tick": 122, "interact": False},
                {"tick": 485, "interact": True},
                {"tick": 486, "interact": False, "move": [1, -0.86]},
                {"tick": 625, "move": [0, 0], "interact": True},
                {"tick": 626, "interact": False},
            ))
            code, err = run_headless("--mode", "quan", "--seed", "7", "--ticks", "1250",
                                     "--inventory", inv, "--inputs", inp_q, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            q_rows = read_jsonl(w.path("q.jsonl"))
            self.assertEqual(len(events(q_rows, "customer_arrived")), 1)
            self.assertEqual(len(events(q_rows, "cook_started")), 1)
            self.assertEqual(len(events(q_rows, "dish_ready")), 1)
            self.assertEqual(len(events(q_rows, "dish_picked")), 1)
            self.assertEqual(len(events(q_rows, "served")), 1)
            self.assertEqual(len(events(q_rows, "paid")), 1)
            # Giá chốt: floor(60 * (99.625 - 122/240) / 100) = floor(59.47) = 59; boa = floor(59 * 0.2) = 11 -> tổng 70
            self.assertEqual(q_rows[-1]["money"], 70)
            self.assertEqual(q_rows[-1]["earned"], 70)
            self.assertEqual(q_rows[-1]["reputation"], 3.2)
            self.assertEqual(q_rows[-1]["score"], 370)


if __name__ == "__main__":
    unittest.main()
