# Changelog

## Phase 3 (`phase-3`) — 2026-11-21 — BREAKING CHANGE (Contract v1.2 “Mùa Nước Nổi”)

### Breaking Changes (v1.1 → v1.2)
- **Đổi schema kho đếm → kho cá thể (`inventory.json`, `scenario.gather.hold`, `scenario.quan.stock`, snapshot `hold`/`stock`, `gather_end.data.inventory`):**
  - Cũ (v1.0/v1.1): `{"items": {"ca_loc": 1}}`, `hold: ["ca_loc"]`, `stock: {"ca_loc": 1}`, `customers[].reserved: {"ca_loc": 1}`.
  - Mới (v1.2): `{"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}`, `hold: [{"id": "I1", "kind": "ca_loc", "fresh": 100}]`, `stock: [...]`, `customers[].reserved: ["I1"]`.
  - File kho đếm v1.0/v1.1 bị từ chối với mã thoát `2` trước khi ghi đầu ra.
- **Đổi payload sự kiện:**
  - `cook_started.data.items`: mảng cá thể sắp theo `(kind, id)` thay vì dict đếm.
  - `monster_hit.data.lost` & `faint.data.lost`: mảng cá thể theo thứ tự bỏ LIFO thay vì mảng chuỗi `kind`.
  - `cook_started.data.base_price`: chốt theo độ tươi trung bình `floor(giá niêm yết × avg_fresh / 100)` (thay vì giá niêm yết cố định), kéo theo tiền boa tính trên `base_price` đã chốt.
- **Cách cập nhật fixture:** Đổi mọi `hold`/`stock`/`inventory.items` sang mảng `{"id": "I1", "kind": "...", "fresh": 100}` (có sẵn tiện ích `items_v12(...)` trong `tests/helpers.py`) và đổi `customers[].reserved` sang mảng id cá thể `["I1", ...]`.

### Tính năng mới & Cải tiến
- **Manifest v1.2 (`game.contract.json`, `chonoi/contract.py`):** đặt `contract_version: "1.2"`, bổ sung `tuning.freshness = {initial: 100, gather_decay_per_s: 0.5, quan_decay_per_s: 0.25, spoiled_below: 30}`.
- **Độ tươi chính xác (`chonoi/inventory.py`, `chonoi/sim/gather.py`, `chonoi/sim/quan.py`, `chonoi/sim/day.py`, `chonoi/sim/shop.py`):** dùng `fractions.Fraction` (`-1/120`/tick ở giỏ, `-1/240`/tick ở quán), phát `spoiled` đúng tick vượt ngưỡng `< 30` theo `id`, cấp `I1, I2, ...` tăng liên tục xuyên pha/Ngày, tự động nhả & thử giữ lại 1 lần khi hàng giữ bị ươn (chuyển `unfulfillable` nếu thiếu), `Pause` dừng hao tươi, kho dư ở Shop không hao tươi.
- **HUD độ tươi (`chonoi/web/index.html`):** hiển thị thanh/số `%` độ tươi từng ô giỏ, cảnh báo đỏ `Ươn` khi `fresh < 30` ở cả buổi sáng, buổi tối, màn chuyển pha và Shop.
- **Kiểm thử & Bằng chứng:** 77/77 test xanh (7 ca mới `tests/test_freshness_p3.py` + regression P1–P2 đã chuyển schema v1.2), ADR-0001, proof tại `docs/proof/phase-3/` và `docs/verification/phase-3.md`.

## Phase 2 (`phase-2`) — 2026-11-21
- Nâng cấp Test Contract v1.1: 6 nguyên liệu, 6 món, 6 nút hái, 2 bếp `B1–B2`, 4 bàn `T1–T4`, cá bơi phản xạ mép + sinh cá `360·k`, Cá Sấu `M1`/`M2`, `--mode day --days 1..5`, Shop `oxygen`/`hp`, Pause cả 3 mode, Menu & HUD.

## Phase 1 (`phase-1`) — 2026-11-21
- Hoàn thiện 4 lát lõi v1.0 (`gather` + `quan`), kiểm mâu thuẫn scenario, E2E 2 tiến trình, skills `.agents/skills/` và bằng chứng `docs/proof/phase-1/`.
