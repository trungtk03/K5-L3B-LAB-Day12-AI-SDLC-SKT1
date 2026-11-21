"""Khung kiểm thử mẫu dành cho Nhóm trưởng (Lát 3 & Lát 4: Quán).

Sau khi hoàn thành các phần việc [PHẦN VIỆC CẦN LÀM] trong `chonoi/sim/quan.py`,
bỏ comment các hàm test dưới đây để chạy kiểm chứng:

    python3 -m unittest tests/test_quan_lat3_lat4.py -v
"""

import json
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


class TestQuanLat3Lat4(unittest.TestCase):
    def test_quan_00_starter_fixture(self):
        """Khung kiểm thử mẫu: Quán khởi động bình thường với bàn T1 và bếp B1."""
        with Workdir() as w:
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "10",
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            s = snapshots(rows)[0]
            self.assertEqual(len(s["stoves"]), 1)
            self.assertEqual(len(s["tables"]), 1)

    # TODO(Nhóm trưởng): Bỏ comment test này khi hoàn thành Lát 3 (sinh khách & no_dish)
    # def test_quan_lat3_customer_arrived_or_no_dish(self):
    #     with Workdir() as w:
    #         # Kho rỗng -> tick 120 sẽ phát no_dish
    #         code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "130",
    #                                  "--out", w.path("q.jsonl"))
    #         self.assertEqual(code, 0, err)
    #         rows = read_jsonl(w.path("q.jsonl"))
    #         self.assertGreaterEqual(len(events(rows, "no_dish")), 1)

    # TODO(Nhóm trưởng): Bỏ comment test này khi hoàn thành Lát 4 (nấu & phục vụ)
    # def test_quan_lat4_cook_and_serve(self):
    #     pass


if __name__ == "__main__":
    unittest.main()
