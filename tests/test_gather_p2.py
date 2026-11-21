"""Bộ kiểm thử Phase 2 cho Buổi sáng (Gather v1.1):
- 6 nút hái (gồm kèo nèo), 3 loài cá (gồm cá kèo), 8 đàn đầu ca
- Đàn cá bơi 1.5 m/s, đổi hướng mỗi 120 tick, phản xạ mép/góc, sinh cá theo lịch 360*k (trần 12)
- Ngạt tính cả bước oxy chạm 0, xuyên bất tử và không rơi hàng
- Cá Sấu Năm Chèo (M1/M2): patrol / chase / recoil, chạm rơi floor(n/2) LIFO, invuln 90 tick, ngất do quái.
"""

import json
import math
import os
import unittest

from helpers import Workdir, close, events, frames, items_v12, read_jsonl, run_headless, snapshots, write_json


class TestGatherP2(unittest.TestCase):
    def test_p2_gather_01_initial_8_fish_6_nodes_and_m1(self):
        """Khởi tạo gather độc lập: 8 đàn cá ở 8 vị trí hình học khác nhau, 6 nút (có kèo nèo), 1 Cá Sấu M1."""
        with Workdir() as w:
            code, err = run_headless("--mode", "gather", "--seed", "7", "--ticks", "0",
                                     "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            s0 = snapshots(read_jsonl(w.path("g.jsonl")))[0]
            self.assertEqual(len(s0["nodes"]), 6)
            self.assertEqual({n["kind"] for n in s0["nodes"]}, {"bong_dien_dien", "bong_sung", "keo_neo"})
            self.assertEqual(len(s0["fish"]), 8)
            pts = {(f["pos"][0], f["pos"][1]) for f in s0["fish"]}
            self.assertEqual(len(pts), 8, "8 đàn đầu ca phải ở 8 vị trí khác nhau")
            self.assertEqual(len(s0["monsters"]), 1)
            self.assertEqual(s0["monsters"][0]["id"], "M1")
            self.assertEqual(s0["monsters"][0]["pos"], [60.0, 24.0])

    def test_p2_gather_02_catch_ca_keo_and_gather_keo_neo(self):
        """Hái kèo nèo (N5) và bắt cá kèo (yield 2)."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [76, 0]},
                    "fish": [{"id": "F1", "kind": "ca_keo", "pos": [76, 24], "heading_deg": 0}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            g_evs = events(read_jsonl(w.path("g.jsonl")), "gather")
            self.assertEqual(len(g_evs), 1)
            self.assertEqual(g_evs[0]["data"]["kind"], "keo_neo")

            # Bắt cá kèo ở d=24
            sc2 = write_json(w.path("sc2.json"), {
                "gather": {
                    "player": {"pos": [76, 24]},
                    "fish": [{"id": "F1", "kind": "ca_keo", "pos": [76, 24], "heading_deg": 0}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            inp2 = write_json(w.path("in2.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc2, "--inputs", inp2, "--out", w.path("g2.jsonl"))
            self.assertEqual(code, 0, err)
            rows2 = read_jsonl(w.path("g2.jsonl"))
            fc = events(rows2, "fish_caught")
            self.assertEqual(len(fc), 1)
            self.assertEqual(fc[0]["data"], {"fish_id": "F1", "kind": "ca_keo", "yield": 2})
            self.assertEqual([it["kind"] for it in snapshots(rows2)[-1]["hold"]], ["ca_keo", "ca_keo"])

    def test_p2_gather_03_fish_swim_reflection_and_turn_at_120(self):
        """Đàn cá bơi 1.5 m/s, phản xạ mép x/d đúng phần dư, chạm góc đảo cả 2 thành phần, đổi hướng ở bước 120."""
        with Workdir() as w:
            # Đặt cá lóc sát góc [95.99, 19.99] hướng 45° -> bước 1 chạm cả mép x=96 và d=20 -> phản xạ góc về 225°
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [2, 0]},
                    "fish": [{"id": "F1", "kind": "ca_loc", "pos": [95.99, 19.99], "heading_deg": 45.0, "age_ticks": 0}],
                    "random_fish": True,
                    "monsters": [],
                }
            })
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "122",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            snaps = {s["tick"]: s for s in snapshots(read_jsonl(w.path("g.jsonl")))}
            f1 = snaps[1]["fish"][0]
            self.assertEqual(f1["age_ticks"], 1)
            self.assertTrue(close(f1["heading_deg"], 225.0, 0.2), f1)
            self.assertLessEqual(f1["pos"][0], 96.0)
            self.assertLessEqual(f1["pos"][1], 20.0)

            # Kiểm đổi hướng ở age_ticks == 120 (bước 120 trước khi di chuyển)
            h119 = snaps[119]["fish"][0]["heading_deg"]
            h120 = snaps[120]["fish"][0]["heading_deg"]
            self.assertNotAlmostEqual(h119, h120, places=2)

    def test_p2_gather_04_fish_scheduled_spawn_at_360_and_cap_12(self):
        """Tại phase_tick = 360*k sinh thêm tối đa 1 đàn cá nếu < 12 đàn, không vượt trần 12."""
        with Workdir() as w:
            code, err = run_headless("--mode", "gather", "--seed", "5", "--ticks", "1850",
                                     "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            spawns = events(rows, "fish_spawned")
            # Khởi đầu 8 đàn -> trần 12 nên sinh tối đa 4 đàn ở tick 360, 720, 1080, 1440 (tick 1800 đã đạt 12!)
            self.assertEqual(len(spawns), 4)
            self.assertEqual([e["tick"] for e in spawns], [360, 720, 1080, 1440])
            self.assertEqual(len(snapshots(rows)[-1]["fish"]), 12)

    def test_p2_gather_05_choke_counts_zero_tick_and_ignores_invuln(self):
        """Ngạt tính cả bước oxy vừa chạm 0 (oxygen_ticks=1 -> tick 1 oxygen_empty, tick 60 choke) và xuyên bất tử."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [20, 5], "oxygen_ticks": 1, "hp": 3, "invuln_ticks": 80},
                    "hold": items_v12("ca_loc", "bong_sung"),
                    "random_fish": False,
                    "monsters": [],
                }
            })
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "65",
                                     "--scenario", sc, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            self.assertEqual(events(rows, "oxygen_empty")[0]["tick"], 1)
            chokes = events(rows, "choke")
            self.assertEqual(len(chokes), 1)
            self.assertEqual(chokes[0]["tick"], 60)
            self.assertEqual(chokes[0]["data"]["hp"], 2)
            # Ngạt không làm rơi hàng trong giỏ
            self.assertEqual([it["kind"] for it in snapshots(rows)[-1]["hold"]], ["ca_loc", "bong_sung"])

    def test_p2_gather_06_monster_patrol_chase_hit_recoil_invuln(self):
        """Cá Sấu patrol -> chase khi d>=10 & dist<=10m -> hit mất 1 HP, rơi floor(n/2) LIFO, invuln 90, recoil 60."""
        with Workdir() as w:
            # Người chơi tại [60, 24] mang 5 món -> chạm ngay bước 1 (trùng tâm recoil_dir = +x)
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [60, 24], "hp": 3},
                    "hold": items_v12("ca_loc", "bong_sung", "ca_linh", "keo_neo", "ca_keo"),  # 5 món -> rơi floor(5/2)=2 LIFO
                    "random_fish": False,
                }
            })
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "70",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            snaps = {s["tick"]: s for s in snapshots(rows)}
            hits = events(rows, "monster_hit")
            self.assertEqual(len(hits), 1, "Trong thời gian bất tử & recoil không bị hit thêm")
            self.assertEqual(hits[0]["tick"], 1)
            self.assertEqual(hits[0]["data"]["monster_id"], "M1")
            self.assertEqual(hits[0]["data"]["hp"], 2)
            # LIFO (v1.2): 2 cá thể nhặt sau cùng là I5 ca_keo, I4 keo_neo
            self.assertEqual([it["id"] for it in hits[0]["data"]["lost"]], ["I5", "I4"])
            self.assertEqual([it["kind"] for it in hits[0]["data"]["lost"]], ["ca_keo", "keo_neo"])
            self.assertEqual([it["kind"] for it in snaps[1]["hold"]], ["ca_loc", "bong_sung", "ca_linh"])
            self.assertEqual(snaps[1]["player"]["invuln_ticks"], 90)
            m1_t1 = snaps[1]["monsters"][0]
            self.assertEqual(m1_t1["state"], "recoil")
            self.assertEqual(m1_t1["state_ticks_left"], 60)
            self.assertEqual(m1_t1["recoil_dir"], [1.0, 0.0])  # trùng tâm dùng +x

            # Sau 60 bước recoil (tại tick 61): M1 đã lùi 2m về x=62 và quay lại patrol
            m1_t61 = snaps[61]["monsters"][0]
            self.assertEqual(m1_t61["state"], "patrol")
            self.assertEqual(m1_t61["state_ticks_left"], 0)
            self.assertTrue(close(m1_t61["pos"][0], 62.0, 0.05), m1_t61)

    def test_p2_gather_07_monster_hit_causes_faint(self):
        """Máu còn 1 gặp Cá Sấu chạm -> monster_hit -> faint(cause='monster') -> gather_end(fainted) kho rỗng."""
        with Workdir() as w:
            inv = w.path("inv.json")
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [60, 24], "hp": 1},
                    "hold": items_v12("ca_loc", "bong_sung", "ca_keo"),  # 3 món: hit rơi 1 (I3), faint rơi 2 còn lại (I2, I1)
                    "random_fish": False,
                }
            })
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "10",
                                     "--scenario", sc, "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            mh = events(rows, "monster_hit")
            fn = events(rows, "faint")
            ge = events(rows, "gather_end")
            self.assertEqual(len(mh), 1)
            self.assertEqual([it["kind"] for it in mh[0]["data"]["lost"]], ["ca_keo"])
            self.assertEqual(len(fn), 1)
            self.assertEqual(fn[0]["data"]["cause"], "monster")
            self.assertEqual([it["kind"] for it in fn[0]["data"]["lost"]], ["bong_sung", "ca_loc"])
            self.assertEqual(fn[0]["data"]["hp"], 0)
            self.assertEqual(ge[0]["data"], {"reason": "fainted", "inventory": {"items": []}})
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})

    def test_p2_gather_08_monster_exits_chase_above_10m_depth(self):
        """Người chơi nổi lên d < 10 -> Cá Sấu rời chase trở về patrol."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [60, 9.5]},  # d < 10
                    "random_fish": False,
                    "monsters": [{
                        "id": "M1",
                        "kind": "ca_sau",
                        "pos": [60, 12],
                        "waypoints": [[60, 12], [64, 12]],
                        "state": "chase",
                    }],
                }
            })
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            s1 = snapshots(read_jsonl(w.path("g.jsonl")))[1]
            self.assertEqual(s1["monsters"][0]["state"], "patrol")


if __name__ == "__main__":
    unittest.main()
