"""Bộ kiểm thử Phase 4 — Phát hành v1.0.0 (Test Contract v1.3):
- Manifest v1.3 khai bench_cmd & soak_cmd
- Benchmark có render 1280x720 xuất đủ 5 trường JSON và kiểm lỗi tham số mã 2
- Soak headless 10 Ngày (lặp D1–D5 ở D6–D10), 0 crash, tất định kết quả gameplay
- 3 cảnh báo chữ + biểu tượng & chế độ tương phản cao trên UI
- Đóng gói bản phát hành zip giải nén sạch và chạy được ngay.
"""

import json
import os
import shlex
import subprocess
import sys
import unittest
import zipfile

from helpers import ROOT, Workdir


def _cmd_from_contract(key: str):
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        cmd = shlex.split(json.load(f)[key])
    if sys.platform == "win32" and cmd and cmd[0] == "python3":
        cmd[0] = sys.executable
    return cmd


class TestReleaseP4(unittest.TestCase):
    def test_p4_01_manifest_v13_declares_bench_and_soak(self):
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["contract_version"], "1.3")
        self.assertIn("bench_cmd", c)
        self.assertIn("soak_cmd", c)
        self.assertTrue(os.path.exists(os.path.join(ROOT, "LICENSE")))
        self.assertTrue(os.path.exists(os.path.join(ROOT, "CREDITS.md")))

    def test_p4_02_bench_cmd_produces_valid_json_and_rejects_bad_args(self):
        with Workdir() as w:
            out = w.path("bench.json")
            p = subprocess.run([*_cmd_from_contract("bench_cmd"), "--seed", "42",
                                "--duration", "0.5", "--warmup", "0.1", "--out", out],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(set(data.keys()), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
            self.assertGreater(data["frames"], 0)
            self.assertGreater(data["measured_s"], 0)
            self.assertGreater(data["avg_fps"], 0)
            self.assertGreater(data["p1_low_fps"], 0)
            self.assertLessEqual(data["p1_low_fps"], data["avg_fps"] + 0.1)
            self.assertGreaterEqual(data["load_ms"], 0)

            bad_out = w.path("bad_bench.json")
            p_bad = subprocess.run([*_cmd_from_contract("bench_cmd"), "--seed", "42",
                                    "--duration", "0", "--out", bad_out],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p_bad.returncode, 2)
            self.assertFalse(os.path.exists(bad_out))

    def test_p4_03_soak_cmd_10_days_zero_crashes_and_deterministic(self):
        with Workdir() as w:
            s1, s2 = w.path("soak1.json"), w.path("soak2.json")
            for target in (s1, s2):
                p = subprocess.run([*_cmd_from_contract("soak_cmd"), "--seed", "7",
                                    "--days", "10", "--out", target],
                                   cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
            with open(s1, encoding="utf-8") as f1, open(s2, encoding="utf-8") as f2:
                d1, d2 = json.load(f1), json.load(f2)

            self.assertEqual(set(d1.keys()), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual(d1["days"], 10)
            self.assertEqual(d1["days_completed"], 10)
            self.assertEqual(d1["crashes"], 0)
            self.assertEqual(len(d1["results"]), 10)
            self.assertEqual([r["day"] for r in d1["results"]], list(range(1, 11)))
            for r in d1["results"]:
                self.assertEqual(set(r.keys()), {"day", "earned", "reputation", "score"})
            self.assertGreater(d1["results"][-1]["earned"], 0)
            # Tính lặp ở các trường gameplay (bỏ duration_s)
            self.assertEqual(d1["results"], d2["results"])
            self.assertEqual(d1["days_completed"], d2["days_completed"])
            self.assertEqual(d1["crashes"], d2["crashes"])

            # --days 0 phải trả mã 2 trước khi ghi file
            bad = w.path("bad_soak.json")
            p_bad = subprocess.run([*_cmd_from_contract("soak_cmd"), "--seed", "7",
                                    "--days", "0", "--out", bad],
                                   cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p_bad.returncode, 2)
            self.assertFalse(os.path.exists(bad))

    def test_p4_04_ui_has_three_accessible_alerts_and_high_contrast(self):
        with open(os.path.join(ROOT, "chonoi", "web", "index.html"), encoding="utf-8") as f:
            html = f.read()
        for token in ("THỦY QUÁI GẦN", "OXY SẮP HẾT", "SẮP GIẬN", "Tương phản cao", "highContrast"):
            self.assertIn(token, html, f"Thiếu cảnh báo/chế độ '{token}' trong UI")

    def test_p4_05_clean_release_package_extracts_and_runs(self):
        with Workdir() as w:
            pkg = w.path("release.zip")
            p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "package_release.py"),
                                "--out", pkg], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            extract_dir = w.path("clean")
            with zipfile.ZipFile(pkg) as zf:
                zf.extractall(extract_dir)
            app_dir = os.path.join(extract_dir, "quan-an-cho-noi-v1.0.0")
            self.assertTrue(os.path.exists(os.path.join(app_dir, "run.sh")))
            self.assertTrue(os.path.exists(os.path.join(app_dir, "LICENSE")))
            out_jsonl = w.path("clean_day.jsonl")
            p2 = subprocess.run([sys.executable, "-m", "chonoi.headless",
                                 "--mode", "day", "--days", "1", "--seed", "1", "--ticks", "60",
                                 "--out", out_jsonl], cwd=app_dir, capture_output=True, text=True)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertTrue(os.path.exists(out_jsonl))


if __name__ == "__main__":
    unittest.main()
