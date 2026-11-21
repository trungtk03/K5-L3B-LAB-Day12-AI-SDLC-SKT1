"""Vòng tick (Contract B v1.1): hỗ trợ gather, quan, day, pause cả 3 mode, đổi pha cùng tick.

Thứ tự ghi:
  - snapshot tick 0 (+ sự kiện khởi tạo tick 0 của day: day_start, day_plan, phase_start)
  - mỗi bước: xét cạnh pause trước -> sự kiện (theo thứ tự xử lý) -> snapshot (nếu tới lượt, đổi pha hoặc kết thúc)
  - dòng 'end' (thêm days_completed ở mode day).
"""

import math
import os

from .errors import BadInput
from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    if mode == "quan":
        return QuanSim(tuning, scenario, streams, ids, inventory=inventory)
    return DaySim(tuning, scenario, streams, ids, days=days)


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning["score"]["reputation_multiplier"]
    return {
        "type": "snapshot",
        "tick": tick,
        "sim_tick": sim_tick,
        "mode": sim.mode,
        "phase": sim.phase,
        "phase_tick": phase_tick,
        "state": state,
        "time_left_ticks": sim.time_left_ticks,
        "money": sim.money,
        "earned": sim.earned,
        "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick (có pause), lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days=days)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False

    @property
    def done(self) -> bool:
        return self.sim.done

    def _state_str(self) -> str:
        if self.sim.done:
            return "finished"
        return "paused" if self.paused else "playing"

    def _event_row(self, tick, phase, name, data, day=None) -> dict:
        row = {"type": "event", "tick": tick, "phase": phase, "name": name, "data": data}
        if self.mode == "day":
            row["day"] = day if day is not None else self.sim.day
        return row

    def init_events(self) -> list:
        """Các sự kiện khởi tạo ở tick 0 (chỉ có ở --mode day)."""
        if self.mode == "day":
            return [
                self._event_row(0, phase, name, data, day=day)
                for phase, day, name, data in self.sim.pop_init_events()
            ]
        return []

    def snapshot(self) -> dict:
        pt = getattr(self.sim, "phase_tick", self.sim_tick)
        s = _common(self.sim, self.tick, self.sim_tick, pt, self.tuning, self._state_str())
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp`; xét cạnh pause trước theo Contract v1.1 mục 4.2."""
        out = []
        self.tick += 1

        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                out.append(self._event_row(self.tick, self.sim.phase, "paused", {}))
                return out
            self.paused = False
            out.append(self._event_row(self.tick, self.sim.phase, "resumed", {}))

        if self.paused:
            return out

        self.sim_tick += 1
        raw_events = self.sim.step(inp)
        if self.mode == "day":
            for phase, day, name, data in raw_events:
                out.append(self._event_row(self.tick, phase, name, data, day=day))
        else:
            for name, data in raw_events:
                out.append(self._event_row(self.tick, self.sim.phase, name, data))
        return out

    def end_row(self) -> dict:
        sim = self.sim
        score = _common(sim, self.tick, self.sim_tick, getattr(sim, "phase_tick", self.sim_tick), self.tuning, "")["score"]
        row = {
            "type": "end",
            "ticks": self.tick,
            "sim_tick": self.sim_tick,
            "mode": sim.mode,
            "state": self._state_str(),
            "reason": sim.reason if sim.done else "tick_limit",
            "money": sim.money,
            "earned": sim.earned,
            "reputation": sim.reputation,
            "score": score,
        }
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every,
        inventory=None, inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    failed_bad_input = False
    try:
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        for row in sess.init_events():
            w.write(row)
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            prev_phase = sess.sim.phase
            prev_day = getattr(sess.sim, "day", None)
            prev_paused = sess.paused
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            phase_changed = (sess.sim.phase != prev_phase or getattr(sess.sim, "day", None) != prev_day)
            pause_changed = (sess.paused != prev_paused)
            if sess.tick % snapshot_every == 0 or sess.done or phase_changed or pause_changed:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    except BadInput:
        failed_bad_input = True
        raise
    finally:
        w.close()
        if failed_bad_input and os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
