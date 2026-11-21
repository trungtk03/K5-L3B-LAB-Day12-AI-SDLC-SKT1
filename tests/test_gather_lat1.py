"""Unit tests cho Lát 1: Bơi, lặn/nổi, oxy, ngạt, Máu và ngất."""

import json
import os
import unittest

from helpers import Workdir, events, frames, items_v12, read_jsonl, run_headless, snapshots, write_json


class TestGatherLat1(unittest.TestCase):
    def test_lat1_01_dive_and_surface_events(self):
        """Bơi xuống dưới surface_depth (0.5m) phát 'dive', bơi lên lại phát 'surface'."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {"player": {"pos": [20, 0.4]}}})
            # Tick 0: bơi xuống (d tăng), tick 10: bơi lên (d giảm)
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "move": [0, 1]},
                {"tick": 10, "move": [0, -1]}
            ))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "50",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            dive_evs = events(rows, "dive")
            surf_evs = events(rows, "surface")
            self.assertGreaterEqual(len(dive_evs), 1)
            self.assertGreaterEqual(len(surf_evs), 1)
            # Tọa độ tại dive phải có d > 0.5
            self.assertGreater(dive_evs[0]["data"]["pos"][1], 0.5)
            # Tọa độ tại surface phải có d <= 0.5
            self.assertLessEqual(surf_evs[0]["data"]["pos"][1], 0.5)

    def test_lat1_02_oxygen_empty_event(self):
        """Dưới nước: oxy trừ dần, khi chạm 0 phát oxygen_empty."""
        with Workdir() as w:
            # Cho oxy còn 5 tick, dưới nước tại d = 5
            sc = write_json(w.path("sc.json"), {"gather": {"player": {"pos": [20, 5], "oxygen_ticks": 5}}})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "10",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            oxy_empty = events(rows, "oxygen_empty")
            self.assertEqual(len(oxy_empty), 1)
            self.assertEqual(oxy_empty[0]["tick"], 5)
            self.assertEqual(oxy_empty[0]["data"]["oxygen_ticks"], 0)

    def test_lat1_03_choke_every_60_ticks(self):
        """Khi oxy = 0 dưới nước, mỗi 60 tick bị choke trừ 1 HP."""
        with Workdir() as w:
            # Bắt đầu tại d=5 với oxy = 0, zero_oxy_ticks = 0, hp = 3
            sc = write_json(w.path("sc.json"), {"gather": {"player": {"pos": [20, 5], "oxygen_ticks": 0, "hp": 3}}})
            # Chạy 125 tick -> sẽ có 2 lần choke: ở tick 60 (hp còn 2) và tick 120 (hp còn 1)
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "125",
                                     "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            chokes = events(rows, "choke")
            self.assertEqual(len(chokes), 2)
            self.assertEqual(chokes[0]["tick"], 60)
            self.assertEqual(chokes[0]["data"]["hp"], 2)
            self.assertEqual(chokes[1]["tick"], 120)
            self.assertEqual(chokes[1]["data"]["hp"], 1)

    def test_lat1_04_surface_resets_zero_oxy_ticks_and_refills(self):
        """Nổi lên mặt nước reset zero_oxy_ticks và hồi 6 tick oxy/bước."""
        with Workdir() as w:
            # Ở dưới nước 30 tick (zero_oxy_ticks = 30), sau đó nổi lên mặt nước
            sc = write_json(w.path("sc.json"), {"gather": {"player": {"pos": [20, 0.6], "oxygen_ticks": 0, "zero_oxy_ticks": 30}}})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "move": [0, -1]}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            last_p = snapshots(rows)[-1]["player"]
            self.assertTrue(last_p["at_surface"])
            self.assertEqual(last_p["zero_oxy_ticks"], 0)
            self.assertGreater(last_p["oxygen_ticks"], 0)

    def test_lat1_05_faint_empties_inventory_and_ends_gather(self):
        """Khi Máu về 0 -> ngất (faint), mất hết giỏ (LIFO), gather_end fainted, file kho rỗng."""
        with Workdir() as w:
            inv = w.path("inv.json")
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [20, 5], "oxygen_ticks": 0, "hp": 1, "zero_oxy_ticks": 59},
                    "hold": items_v12("ca_loc", "bong_dien_dien", "ca_linh"),
                }
            })
            # Bước tiếp theo (tick 1) zero_oxy_ticks đạt 60 -> choke -> hp = 0 -> faint!
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "10",
                                     "--scenario", sc, "--inventory-out", inv, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            faint_evs = events(rows, "faint")
            self.assertEqual(len(faint_evs), 1)
            self.assertEqual(faint_evs[0]["tick"], 1)
            self.assertEqual(faint_evs[0]["data"]["cause"], "choke")
            # Thứ tự lost (v1.2): mảng cá thể LIFO (I3 ca_linh, I2 bong_dien_dien, I1 ca_loc)
            self.assertEqual([it["kind"] for it in faint_evs[0]["data"]["lost"]], ["ca_linh", "bong_dien_dien", "ca_loc"])
            self.assertEqual([it["id"] for it in faint_evs[0]["data"]["lost"]], ["I3", "I2", "I1"])
            self.assertEqual(faint_evs[0]["data"]["hp"], 0)

            # gather_end reason fainted với kho rỗng []
            gather_end = events(rows, "gather_end")
            self.assertEqual(len(gather_end), 1)
            self.assertEqual(gather_end[0]["data"]["reason"], "fainted")
            self.assertEqual(gather_end[0]["data"]["inventory"], {"items": []})

            # File kho được ghi ra rỗng {"items": []}
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})


if __name__ == "__main__":
    unittest.main()
