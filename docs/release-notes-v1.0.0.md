# Release Notes — Quán Ăn Chợ Nổi v1.0.0 (Nhóm SKT1)

> Commit phát hành tương ứng với tag `phase-4` và `v1.0.0` trên nhánh `main` · Test Contract `v1.3` · Giấy phép MIT.

## Điểm mới nổi bật (v1.0.0)
- **Vòng chơi trọn vẹn 5 Ngày (Phase 1–2):**
  - Buổi sáng (`gather`): Út Sen lặn bắt 3 loài cá (`ca_linh`, `ca_loc`, `ca_keo`) biết bơi, đổi hướng định kỳ, phản xạ mép và sinh theo lịch; hái 3 loại rau mặt nước (`bong_dien_dien`, `bong_sung`, `keo_neo`); né Cá Sấu Năm Chèo (`M1` từ Ngày 1, `M2` từ Ngày 3) với hành vi `patrol`/`chase`/`recoil`.
  - Buổi tối (`quan`): Nhà bè 2 bếp (`B1–B2`), 4 bàn (`T1–T4`), 6 món miền Tây theo kế hoạch Ngày `D1–D5` của Má Tư, tính boa & uy tín.
  - Cửa hàng cuối ngày (`shop`): Nâng cấp Bình oxy (`45s` / `60s`) và Áo phao (`4` / `5` Máu) có hiệu lực từ Ngày kế tiếp.
- **Độ tươi từng cá thể — “Mùa Nước Nổi” (Phase 3 · Contract v1.2):**
  - Kho cá thể `{id, kind, fresh}` với `id` (`I1, I2, ...`) tăng liên tục xuyên pha/Ngày; hao tươi chính xác bằng `fractions.Fraction` (`-0.5/s` giỏ, `-0.25/s` kho quán), ngưỡng ươn `< 30` (`spoiled`), giữ chỗ theo `id` tươi nhất, tự nhả & thử giữ lại 1 lần khi hàng giữ vừa ươn, giá món chốt theo độ tươi trung bình `floor(price × avg_fresh / 100)`.
- **Đo hiệu năng, Soak 10 Ngày & Khả năng tiếp cận (Phase 4 · Contract v1.3):**
  - Benchmark có render `1280×720` (`python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json`) và Soak headless 10 Ngày bằng bot tất định (`python3 -m chonoi.soak --seed 7 --days 10 --out soak.json`).
  - Ba cảnh báo trực quan bằng **chữ + biểu tượng** (*Thủy quái gần*, *Oxy sắp hết / Hết hơi*, *Khách sắp giận*) và **Chế độ tương phản cao** (phím `H` hoặc nút trên Menu/Pause/HUD).
  - Gói phát hành chạy ngay không cần cài thư viện ngoài (`quan-an-cho-noi-v1.0.0.zip`).

## Cách chạy (≤ 3 lệnh trên macOS / Linux)
```bash
git clone https://github.com/trungtk03/K5-L3B-LAB-Day12-AI-SDLC-SKT1.git
cd K5-L3B-LAB-Day12-AI-SDLC-SKT1
python3 -m chonoi.live --mode day --days 5
```
Hoặc giải nén tệp đính kèm `quan-an-cho-noi-v1.0.0.zip` và chạy `./run.sh` (macOS/Linux) hoặc `run.bat` (Windows).

## Giới hạn đã biết
- Nhóm SKT1 có quy mô 2 thành viên nên tập trung hoàn thiện 100% lõi Contract `v1.0 → v1.3`, chưa bật các extension tùy chọn (`weapon`, `net`, `snake`, `burn`, `vendor`, `ca_ho`, `current`, `reservations`, `leaderboard`).
- Phiên bản trình duyệt (`chonoi.live`) dùng đồ họa 2D Canvas gọn nhẹ không có âm thanh nền để bảo đảm chạy thuần thư viện chuẩn Python (0 dependency).
- Script cảnh báo `tools/check_team.py` kiểm quy mô mặc định 4–6 thành viên trong khi nhóm thực tế có 2 thành viên (khớp `team_size: 2` trong `game.contract.json`).
