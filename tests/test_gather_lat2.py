"""Unit tests cho Lát 2: Hái nút trên mặt nước, bắt cá dưới nước, sức chứa giỏ và cập bến."""

import json
import unittest

from helpers import Workdir, events, frames, items_v12, read_jsonl, run_headless, snapshots, write_json


class TestGatherLat2(unittest.TestCase):
    def test_lat2_01_gather_node_and_regrow(self):
        """Hái nút khi ở mặt nước: thêm nguyên liệu, phát gather, đặt regrow_ticks."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [12, 0]},
                    "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0], "regrow_ticks": 0}]
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            gathers = events(rows, "gather")
            self.assertEqual(len(gathers), 1)
            self.assertEqual(gathers[0]["data"]["node_id"], "N1")
            self.assertEqual(gathers[0]["data"]["kind"], "bong_dien_dien")
            self.assertEqual(gathers[0]["data"]["amount"], 1)

            # Snapshot sau khi hái (v1.2): hold là mảng cá thể {id, kind, fresh=100}
            s = snapshots(rows)[1]
            self.assertEqual(s["hold"], [{"id": "I1", "kind": "bong_dien_dien", "fresh": 100}])
            node_n1 = next(n for n in s["nodes"] if n["id"] == "N1")
            self.assertFalse(node_n1["ready"])
            self.assertGreater(node_n1["regrow_ticks"], 1190)

    def test_lat2_02_gather_hold_full(self):
        """Hái khi giỏ đã đầy phát hold_full, nút giữ nguyên."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [12, 0]},
                    "hold": items_v12(*(["ca_loc"] * 12)),  # hold_capacity là 12
                    "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12, 0], "regrow_ticks": 0}]
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            hf = events(rows, "hold_full")
            self.assertEqual(len(hf), 1)
            self.assertEqual(hf[0]["data"]["action"], "gather")
            self.assertEqual(hf[0]["data"]["node_id"], "N1")
            self.assertEqual(hf[0]["data"]["required"], 1)
            self.assertEqual(hf[0]["data"]["free"], 0)

    def test_lat2_03_catch_fish_and_cooldown(self):
        """Bắt cá dưới nước: xóa đàn cá, thêm yield vào giỏ, đặt hồi chiêu catch_cooldown."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [15, 5]},
                    "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5], "heading_deg": 0}],
                    "random_fish": False
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5",
                                     "--scenario", sc, "--inputs", inp, "--snapshot-every", "1", "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            fc = events(rows, "fish_caught")
            self.assertEqual(len(fc), 1)
            self.assertEqual(fc[0]["data"]["fish_id"], "F1")
            self.assertEqual(fc[0]["data"]["kind"], "ca_linh")
            self.assertEqual(fc[0]["data"]["yield"], 3)  # ca_linh yield = 3

            # Snapshot sau khi bắt (v1.2): hold có 3 cá thể ca_linh (I1..I3, fresh=100), fish rỗng, catch_cd_ticks dương
            s = snapshots(rows)[1]
            self.assertEqual(s["hold"], items_v12("ca_linh", "ca_linh", "ca_linh"))
            self.assertEqual(len(s["fish"]), 0)
            self.assertGreater(s["player"]["catch_cd_ticks"], 0)

    def test_lat2_04_catch_fish_hold_full(self):
        """Bắt cá khi giỏ không đủ chỗ phát hold_full, giữ nguyên cá và không hồi chiêu."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [15, 5]},
                    "hold": items_v12(*(["ca_loc"] * 10)),  # còn 2 chỗ, nhưng ca_linh cần 3
                    "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5], "heading_deg": 0}],
                    "random_fish": False
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "catch": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            hf = events(rows, "hold_full")
            self.assertEqual(len(hf), 1)
            self.assertEqual(hf[0]["data"]["action"], "catch")
            self.assertEqual(hf[0]["data"]["fish_id"], "F1")
            self.assertEqual(hf[0]["data"]["required"], 3)
            self.assertEqual(hf[0]["data"]["free"], 2)

    def test_lat2_05_tie_breaking_by_id(self):
        """Hai nút cách đều vị trí người chơi: ưu tiên nút có id nhỏ hơn."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "player": {"pos": [10, 0]},
                    "nodes": [
                        {"id": "N2", "kind": "bong_dien_dien", "pos": [11, 0], "regrow_ticks": 0},
                        {"id": "N1", "kind": "bong_dien_dien", "pos": [9, 0], "regrow_ticks": 0}
                    ]
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--inputs", inp, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
            gathers = events(rows, "gather")
            self.assertEqual(len(gathers), 1)
            self.assertEqual(gathers[0]["data"]["node_id"], "N1")


if __name__ == "__main__":
    unittest.main()
