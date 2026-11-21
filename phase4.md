# TICKET-04 — Phát hành v1.0.0 (Phase 4)

> 30 phút (2:30–3:00) · Test Contract v1.3 · Hạn đẩy tag `phase-4` và công bố GitHub Release `v1.0.0` 3:00.

## 1. Lõi (mọi nhóm)
- **Contract v1.3:** Đặt `contract_version: "1.3"`, khai `bench_cmd` và `soak_cmd` ở gốc `game.contract.json`. Gameplay, tuning, kho và JSONL giữ đúng v1.2.
- **Benchmark có render (`<bench_cmd> --seed 42 --duration 30 --out bench.json`):**
  - Cảnh đo: buổi sáng lõi với độ tươi, cá bơi, Cá Sấu Năm Chèo và hiệu ứng mặc định; Út Sen đứng yên ở bến; seed `42`; khung hình `1280×720`; làm nóng `3 s` rồi đo `30 s`.
  - Xuất 5 trường JSON: `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms` (`p1_low_fps` = nghịch đảo thời gian trung bình của `max(1, ceil(0.01 × frames))` khung chậm nhất). Mốc báo cáo: `avg ≥ 60 FPS`, `1% low ≥ 30 FPS`, `load ≤ 10 s`.
- **Soak headless (`<soak_cmd> --seed 7 --days 10 --out soak.json`):**
  - Chạy `N` Ngày (10 Ngày) trong một tiến trình headless bằng bot tất định; mỗi Ngày qua `gather → quan → shop`; kế hoạch D1–D5 lặp ở Ngày 6–10; tiền, tổng thu, uy tín, cấp nâng cấp, số Ngày và `id` cá thể liên tục xuyên suốt.
  - Xuất `soak.json` có `days`, `days_completed`, `crashes`, `results[]` (`day`, `earned`, `reputation`, `score` lúc Shop đóng), `duration_s`. Đạt khi `days_completed == days`, `crashes == 0` và kết quả gameplay tất định.
- **Cảnh báo dễ nhận biết & tương phản cao:** Dùng chữ và biểu tượng cho 3 cảnh báo (thủy quái gần, oxy sắp hết, khách sắp giận) kèm chế độ tương phản cao (`H` / nút trên UI).
- **Đóng gói, Release & Tổng kết:** Clone sạch chạy ≤ 3 lệnh trên macOS/Linux; `README.md` đầy đủ lệnh; `LICENSE`, `CREDITS.md`, `CHANGELOG.md`, `docs/release-notes-v1.0.0.md`, gói đóng gói đính kèm Release `v1.0.0`, `docs/verification/phase-4.md`, `docs/proof/phase-4/`, `docs/retro.md` (rà hành động P2), `docs/members/<handle>.md`, tag `phase-4` & `v1.0.0` cùng trỏ tới commit bàn giao trên `main`.
