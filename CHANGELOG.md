# Changelog

## v1.0.0 / Phase 4 (`phase-4`, `v1.0.0`) — 2026-11-21 — Contract v1.3
- **Test Contract v1.3 (`game.contract.json`):** Đặt `contract_version: "1.3"`, khai `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`) ở gốc manifest; giữ nguyên luật gameplay, tuning, kho cá thể và JSONL của v1.2.
- **Benchmark có render 1280×720 (`chonoi/bench.py`):** Dựng bộ rasterizer phần mềm `1280×720` cho cảnh buổi sáng lõi (seed 42, độ tươi, cá bơi, Cá Sấu M1, làm nóng 3s + đo 30s), xuất đủ 5 trường `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms`.
- **Soak headless nhiều Ngày (`chonoi/soak.py`, `chonoi/sim/day.py`):** Bổ sung lặp kế hoạch `D1–D5` cho Ngày `6–10+` và bot tất định chạy trọn 10 Ngày qua `gather → quan → shop` không crash, xuất `soak.json` tất định.
- **Cảnh báo & Tương phản cao (`chonoi/web/index.html`):** Nâng cấp 3 cảnh báo bằng chữ + biểu tượng (*Thủy quái gần*, *Oxy sắp hết / Hết hơi*, *Khách sắp giận*) và bổ sung **Chế độ tương phản cao** (phím `H` / nút trên Menu, Pause và HUD).
- **Đóng gói & Phát hành (`tools/package_release.py`, `LICENSE`, `CREDITS.md`, `docs/release-notes-v1.0.0.md`):** Thêm giấy phép MIT, rà `CREDITS.md`, script đóng gói `quan-an-cho-noi-v1.0.0.zip` chạy ngay với `run.sh`/`run.bat`, 82/82 test xanh, retro cuối buổi và phản tư cá nhân đầy đủ.

## Phase 3 (`phase-3`) — 2026-11-21 — BREAKING CHANGE (Contract v1.2 “Mùa Nước Nổi”)
- **Breaking Change:** Chuyển kho đếm (`{"items": {"ca_loc": 1}}`) sang kho cá thể (`{"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}`), từ chối kho đếm cũ bằng mã `2`; `customers[].reserved` thành mảng `id`; `cook_started.items` sắp `(kind, id)`; `lost` xuất mảng cá thể LIFO.
- **Độ tươi & giá động:** Dùng `fractions.Fraction` (`-0.5/s` giỏ, `-0.25/s` quán), ngưỡng ươn `< 30` (`spoiled`), thử giữ lại đúng 1 lần khi hàng giữ bị ươn (hoặc `unfulfillable`), giá chốt `floor(price × avg_fresh / 100)`, `Pause` dừng hao tươi, Shop không hao tươi, HUD hiển thị `%` độ tươi và nhãn `Ươn` (ADR-0001).

## Phase 2 (`phase-2`) — 2026-11-21 — Contract v1.1
- Nâng cấp số chuẩn v1.1: 6 nguyên liệu (`ca_keo`, `keo_neo`), 6 món ăn, 6 nút hái `N1–N6`, 2 bếp `B1–B2`, 4 bàn `T1–T4`, cá bơi `1.5 m/s` phản xạ mép/góc + sinh cá `360·k`, Cá Sấu Năm Chèo `M1`/`M2` (`patrol`/`chase`/`recoil`), `--mode day --days 1..5`, Shop nâng cấp `oxygen`/`hp`, Pause cả 3 mode, Menu & HUD `≥ 18px`.

## Phase 1 (`phase-1`) — 2026-11-21 — Contract v1.0
- Hoàn thiện 4 lát lõi v1.0 (`gather` + `quan`), kiểm mâu thuẫn scenario, E2E 2 tiến trình, skills `.agents/skills/` và bằng chứng `docs/proof/phase-1/`.
