"""Benchmark có render 1280x720 cho cảnh Buổi sáng (Contract v1.3).

    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Cảnh đo: Buổi sáng lõi (`GatherSim`) với độ tươi, cá bơi, Cá Sấu Năm Chèo (M1),
Út Sen đứng yên ở bến; cửa sổ 1280×720; làm nóng 3 s rồi đo `--duration` giây.
Xuất 5 trường JSON: avg_fps, p1_low_fps, frames, measured_s, load_ms.
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time

from .contract import load_contract
from .errors import BadInput
from .inputs import BUTTONS_V11, InputState
from .runner import Session

WIDTH = 1280
HEIGHT = 720

KIND_RGB = {
    "ca_loc": bytes((124, 154, 82)),
    "ca_linh": bytes((214, 230, 242)),
    "ca_keo": bytes((217, 160, 102)),
    "bong_dien_dien": bytes((242, 194, 48)),
    "bong_sung": bytes((232, 121, 156)),
    "keo_neo": bytes((104, 199, 112)),
}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


class SoftwareGatherRenderer:
    """Bộ vẽ 2D thực tế ra framebuffer RGB 1280x720 (thuần thư viện chuẩn Python, chạy mọi OS/CI)."""

    def __init__(self, width=WIDTH, height=HEIGHT):
        self.w = width
        self.h = height
        self.stride = width * 3
        self.fb = bytearray(width * height * 3)

        # Dựng sẵn nền tĩnh 1280x720 (HUD trên/dưới, trời hồng sớm, 3 tầng độ sâu nước)
        bg = bytearray(width * height * 3)
        top, bottom = 86, 78
        sky_h = 84
        oy = top + sky_h
        water_h = height - bottom - oy
        y_mid = oy + water_h // 3
        y_deep = oy + (2 * water_h) // 3

        bands = (
            (0, top, (16, 22, 28)),
            (top, oy, (220, 226, 245)),
            (oy, y_mid, (59, 154, 178)),
            (y_mid, y_deep, (31, 96, 122)),
            (y_deep, height - bottom, (11, 36, 56)),
            (height - bottom, height, (16, 22, 28)),
        )
        for y0, y1, rgb in bands:
            row = bytes(rgb) * width
            bg[y0 * self.stride: y1 * self.stride] = row * (y1 - y0)
        self._bg = bytes(bg)
        self._top = top
        self._oy = oy
        self._water_h = water_h
        self._bottom = bottom

    def _fill_rect(self, x0: int, y0: int, rw: int, rh: int, color3: bytes):
        if rw <= 0 or rh <= 0:
            return
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x0 + rw)
        y1 = min(self.h, y0 + rh)
        if x1 <= x0 or y1 <= y0:
            return
        span = color3 * (x1 - x0)
        stride = self.stride
        fb = self.fb
        off = y0 * stride + x0 * 3
        span_len = len(span)
        for _ in range(y1 - y0):
            fb[off: off + span_len] = span
            off += stride

    def render(self, snap: dict, tuning_gather: dict):
        # 1. Nạp nền 1280x720
        self.fb[:] = self._bg
        b = tuning_gather["bounds"]
        max_x = float(b["x"][1])
        max_d = float(b["d"][1])
        sx = lambda x: int(24 + (x / max_x) * (self.w - 48))
        sy = lambda d: int(self._oy + (d / max_d) * self._water_h)

        # 2. Bến
        dx, dy = sx(tuning_gather["dock_pos"][0]), sy(tuning_gather["dock_pos"][1])
        self._fill_rect(dx - 18, dy - 16, 36, 16, bytes((141, 110, 75)))
        self._fill_rect(dx - 22, dy - 30, 44, 14, bytes((185, 80, 58)))

        # 3. 6 nút hái mặt nước
        for n in snap["nodes"]:
            nx, ny = sx(n["pos"][0]), sy(n["pos"][1])
            col = KIND_RGB.get(n["kind"], bytes((200, 200, 200))) if n["ready"] else bytes((90, 100, 110))
            self._fill_rect(nx - 10, ny - 6, 20, 10, col)

        # 4. Đàn cá bơi
        for f in snap["fish"]:
            fx, fy = sx(f["pos"][0]), sy(f["pos"][1])
            col = KIND_RGB.get(f["kind"], bytes((200, 200, 200)))
            self._fill_rect(fx - 10, fy - 5, 20, 10, col)

        # 5. Cá Sấu Năm Chèo (M1/M2)
        for m in snap.get("monsters", ()):
            mx, my = sx(m["pos"][0]), sy(m["pos"][1])
            col = bytes((168, 85, 247)) if m["state"] == "chase" else bytes((77, 124, 15))
            self._fill_rect(mx - 18, my - 8, 36, 16, col)

        # 6. Út Sen (người chơi)
        p = snap["player"]
        px, py = sx(p["pos"][0]), sy(p["pos"][1])
        self._fill_rect(px - 8, py - 8, 16, 16, bytes((255, 138, 61)))

        # 7. HUD trên (thanh oxy, tim HP, thanh thời gian)
        oxy_frac = p["oxygen_ticks"] / max(1, p["oxygen_max_ticks"])
        self._fill_rect(220, 14, 240, 24, bytes((30, 41, 59)))
        self._fill_rect(220, 14, int(240 * oxy_frac), 24, bytes((56, 189, 248)))
        for i in range(p["hp_max"]):
            hcol = bytes((251, 113, 133)) if i < p["hp"] else bytes((71, 85, 105))
            self._fill_rect(480 + i * 26, 14, 20, 20, hcol)

        # 8. HUD dưới (giỏ 12 ô + thanh độ tươi)
        hold = snap["hold"]
        y_hold = self.h - self._bottom + 12
        for i in range(snap["hold_capacity"]):
            x0 = 16 + i * 36
            self._fill_rect(x0, y_hold, 32, 32, bytes((45, 55, 72)))
            if i < len(hold):
                it = hold[i]
                sp = it["fresh"] < 30
                self._fill_rect(x0 + 2, y_hold + 2, 28, 22, bytes((127, 29, 29)) if sp else KIND_RGB.get(it["kind"], bytes((200, 200, 200))))
                fw = int(28 * max(0.0, min(1.0, it["fresh"] / 100.0)))
                self._fill_rect(x0 + 2, y_hold + 26, fw, 4, bytes((239, 68, 68)) if sp else bytes((74, 222, 128)))


def _write_json_atomic(path: str, payload: dict):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".bench-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run_benchmark(seed: int, duration_s: float, warmup_s: float = 3.0) -> dict:
    t_start = time.perf_counter()
    tuning = load_contract()["tuning"]
    g_cfg = tuning["gather"]
    renderer = SoftwareGatherRenderer(WIDTH, HEIGHT)
    idle_inp = InputState((0.0, 0.0), {b: False for b in BUTTONS_V11}, set())

    def new_sess():
        return Session("gather", tuning, {}, seed)

    sess = new_sess()

    def render_one_frame():
        nonlocal sess
        if sess.done:
            sess = new_sess()
        sess.step(idle_inp)
        snap = sess.snapshot()
        renderer.render(snap, g_cfg)

    # Khung hình đầu tiên -> đo load_ms
    render_one_frame()
    load_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

    # Làm nóng (mặc định 3s)
    if warmup_s > 0:
        t_warm_end = time.perf_counter() + warmup_s
        while time.perf_counter() < t_warm_end:
            render_one_frame()

    # Khoảng đo chính (mặc định 30s)
    frame_times = []
    t_meas_start = time.perf_counter()
    t_meas_deadline = t_meas_start + duration_s
    while True:
        f0 = time.perf_counter()
        if f0 >= t_meas_deadline and frame_times:
            break
        render_one_frame()
        f1 = time.perf_counter()
        frame_times.append(max(1e-9, f1 - f0))
        if f1 >= t_meas_deadline:
            break

    measured_s = max(1e-6, time.perf_counter() - t_meas_start)
    frames = len(frame_times)
    avg_fps = frames / measured_s
    k = max(1, math.ceil(0.01 * frames))
    slowest = sorted(frame_times, reverse=True)[:k]
    p1_low_fps = 1.0 / (sum(slowest) / len(slowest))

    return {
        "avg_fps": round(avg_fps, 2),
        "p1_low_fps": round(p1_low_fps, 2),
        "frames": frames,
        "measured_s": round(measured_s, 3),
        "load_ms": load_ms,
    }


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.bench", description="Benchmark có render 1280x720 (Contract v1.3).")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--warmup", type=float, default=3.0)
    a = p.parse_args(argv)
    try:
        if not math.isfinite(a.duration) or a.duration <= 0:
            raise BadInput("--duration phải > 0")
        if not math.isfinite(a.warmup) or a.warmup < 0:
            raise BadInput("--warmup phải >= 0")
        result = run_benchmark(a.seed, a.duration, warmup_s=a.warmup)
        _write_json_atomic(a.out, result)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
