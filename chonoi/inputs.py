"""File inputs (Contract C v1.1): frames, kế thừa trường vắng, cạnh lên (false -> true), buy một bước.

Dùng: ip = InputPlayer(frames); mỗi bước k: state = ip.advance(k)
  state.move -> (x, d) trong gather hoặc (x, z) trong quan, đã chuẩn hóa;
  state.pressed("interact") / ("catch") / ("pause") / ("shop_done") -> True nếu CẠNH LÊN ở bước này;
  state.buy -> chuỗi lệnh mua (chỉ tại đúng frame khai báo, không kế thừa).
"""

import json
import math

from .errors import BadInput

BUTTONS_V10 = ("interact", "catch")
BUTTONS_V11 = ("interact", "catch", "pause", "shop_done")


class InputState:
    def __init__(self, move, held, edges, buy=None):
        self.move = move
        self.held = held
        self._edges = edges
        self.buy = buy

    def pressed(self, name: str) -> bool:
        return name in self._edges


def load_frames(path, buttons=BUTTONS_V11):
    if path is None:
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được inputs {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"frames"} or not isinstance(data["frames"], list):
        raise BadInput("inputs phải có đúng một khóa 'frames' (mảng)")
    last = -1
    frames = []
    allowed = {"tick", "move", "buy", *buttons}
    for i, fr in enumerate(data["frames"]):
        if not isinstance(fr, dict):
            raise BadInput(f"frame {i} không phải object")
        extra = set(fr) - allowed
        if extra:
            raise BadInput(f"frame {i} có trường lạ/chưa hỗ trợ: {sorted(extra)}")
        t = fr.get("tick")
        if isinstance(t, bool) or not isinstance(t, int) or t < 0:
            raise BadInput(f"frame {i}: tick phải là số nguyên >= 0")
        if t <= last:
            raise BadInput(f"frame {i}: tick trùng hoặc giảm")
        last = t
        if "move" in fr:
            m = fr["move"]
            ok = (isinstance(m, list) and len(m) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and math.isfinite(c) and -1 <= c <= 1 for c in m))
            if not ok:
                raise BadInput(f"frame {i}: move phải là [x, d] (gather) hoặc [x, z] (quan), mỗi số trong [-1, 1]")
        for b in buttons:
            if b in fr and not isinstance(fr[b], bool):
                raise BadInput(f"frame {i}: {b} phải là boolean")
        if "buy" in fr:
            if not isinstance(fr["buy"], str) or not fr["buy"]:
                raise BadInput(f"frame {i}: buy phải là chuỗi khác rỗng")
        frames.append(fr)
    return frames


def normalize(move):
    x, y = float(move[0]), float(move[1])
    n = math.hypot(x, y)
    if n > 1:
        return (x / n, y / n)
    return (x, y)


class InputPlayer:
    def __init__(self, frames, buttons=BUTTONS_V11):
        self._frames = {fr["tick"]: fr for fr in frames}
        self._buttons = buttons
        self._move = (0.0, 0.0)
        self._held = {b: False for b in buttons}

    def advance(self, k: int) -> InputState:
        """Đọc input có tick == k. Trả trạng thái dùng cho bước k."""
        edges = set()
        buy = None
        fr = self._frames.get(k)
        if fr:
            if "move" in fr:
                self._move = normalize(fr["move"])
            for b in self._buttons:
                if b in fr:
                    if fr[b] and not self._held[b]:
                        edges.add(b)
                    self._held[b] = fr[b]
            if "buy" in fr:
                buy = fr["buy"]
        return InputState(self._move, dict(self._held), edges, buy=buy)


class LiveInputs:
    """Input trực tiếp (cửa sổ chơi): giữ trạng thái nút, nhớ cạnh lên giữa hai tick để không mất cú bấm nhanh."""

    def __init__(self, buttons=BUTTONS_V11):
        self._buttons = buttons
        self._move = (0.0, 0.0)
        self._held = {b: False for b in buttons}
        self._pending = set()
        self._pending_buy = []

    def set(self, move=None, buy=None, **buttons):
        if move is not None:
            self._move = normalize(move)
        for b, v in buttons.items():
            if b not in self._held:
                continue
            if v and not self._held[b]:
                self._pending.add(b)
            self._held[b] = bool(v)
        if buy is not None:
            self._pending_buy.append(buy)

    def advance(self) -> InputState:
        edges, self._pending = self._pending, set()
        buy = self._pending_buy.pop(0) if self._pending_buy else None
        return InputState(self._move, dict(self._held), edges, buy=buy)
