# Retro nhóm SKT1

## Phase 2 (nhanh)
- **Điều tốt:**
  - Chốt sớm nền Test Contract v1.1 (`game.contract.json`, `contract.py`, `inventory.py`, `inputs.py`, `scenario.py`, `headless.py`) giúp các lát `gather` (cá bơi/sinh, Cá Sấu) và `quan`/`day`/`shop` tích hợp mượt, 15 ca test Phase 2 xanh ngay lần chạy đầu.
  - Hiệu năng headless một Ngày đầy đủ 22.200 tick chỉ ~1.0s (vượt xa ngưỡng ≤ 20s) và tất định 100% từng byte trên cả 3 mode.
- **Điều tệ:**
  - Quy mô nhóm chỉ có 2 người nên áp lực thời gian giữa việc code lõi + giao diện Menu/HUD + xuất bằng chứng khá gấp, chưa kịp làm thêm mở rộng.
  - Một số test Phase 1 hard-code số lượng cũ (`fish=6`, `stoves=1`) phải rà và cập nhật lại khi đổi sang số chuẩn v1.1.
- **1 hành động cho Phase 3 (người nhận: `trungtk03` & `DungNguyen74`):**
  - Mọi test mới từ Phase 3 trở đi luôn đọc hằng số từ `game.contract.json` (không hard-code số lượng bàn/bếp/cá), đồng thời giữ sẵn kịch bản benchmark & smoke tự động để xuất proof trong 1 lệnh duy nhất trước mốc bàn giao 10 phút.

## Phase 3 (nhanh — rút kinh nghiệm đổi schema kho v1.2)
- **Điều tốt:** Phân tích tác động và chốt ADR-0001 (dùng `fractions.Fraction` + helper `items_v12()`) ngay 7 phút đầu giúp chuyển đổi toàn bộ 4 module sim + 77 ca test sang kho cá thể không phát sinh lỗi làm tròn hay vỡ nhánh giữa chừng.
- **Bài học từ breaking change:** Tập trung toàn bộ quy ước đọc/ghi/validate cá thể vào một module duy nhất (`chonoi/inventory.py`) giúp các module sim chỉ phụ thuộc một nguồn chân lý.

## Phase 4 (cuối — tổng kết phát hành v1.0.0)
- **Rà lại hành động Phase 2 — đã làm chưa? vì sao?**
  - **Đã thực hiện đầy đủ 100%:** Ở cả Phase 3 (`test_freshness_p3.py`) và Phase 4 (`test_release_p4.py`), mọi test đều đọc lệnh/cấu hình trực tiếp từ `game.contract.json` (không hard-code), và mỗi phase đều có kịch bản sinh proof tự động gom toàn bộ `unittest.log`, smoke/bench/soak và đối chiếu SHA-256 trong một lượt chạy trước khi gắn tag.
- **Điều tốt / điều tệ:**
  - *Điều tốt:* Hoàn thành trọn vẹn 4 phase đúng tiến độ (Contract `v1.0 → v1.1 → v1.2 → v1.3`), 82/82 test tự động xanh, 0 crash trong Soak 10 Ngày, Benchmark `1280×720` vượt xa mốc 60 FPS, tất định từng byte trên cả 3 mode, tài liệu + ADR + CHANGELOG + Release v1.0.0 hoàn chỉnh và thuần Python stdlib (0 dependency).
  - *Điều tệ:* Do nhóm chỉ có 2 thành viên nên chưa triển khai thêm các extension tùy chọn (`burn`, `vendor`, `current`, `leaderboard`) và đồ họa trình duyệt mới dừng ở 2D Canvas hình khối gọn.
- **Số liệu đóng góp, review & AI token:**
  - *Commit:* `DungNguyen74` (3 commit trực tiếp Phase 1 + đồng tác giả `Co-authored-by` các commit `gather`/test/proof Phase 2–4); `trungtk03` (20+ commit trải đều Phase 1–4 từ Lát 3–4, Contract v1.1–v1.3, `day`/`shop`/`bench`/`soak`, HUD & phát hành `v1.0.0`).
  - *Cách đọc code của nhau:* Review trực tiếp trên commit diff trước khi tích hợp và chạy kiểm chéo bằng bộ test hộp đen + unit trên từng lát.
  - *Token AI ước tính:* `DungNguyen74` ~27k (P1) + pair ~35k (P2–P4); `trungtk03` ~40k (P1) + ~85k (P2–P4) — tổng ~187k tokens (chi tiết tại [`docs/ai-usage-log.md`](ai-usage-log.md)).
- **Một lần AI sai và cách nhóm phát hiện:**
  - *Lỗi 1 (Phase 1):* Quỹ đạo di chuyển của test E2E dừng cách bàn `T1` `1.503 m` (lệch 3 mm ngoài `interact_radius = 1.5 m`) khiến sự kiện `served` không phát; đồng thời phát hiện phép cộng float `0.2` uy tín nhiều lần có thể làm `math.floor(reputation)` lệch 100 điểm. Nhóm phát hiện ngay qua test tự động fail & phân tích biên, sửa vector đi thẳng và làm tròn 6 chữ số sau khi kẹp uy tín.
  - *Lỗi 2 (Phase 1):* File `.gitignore` gốc chặn `*.jsonl` khiến các file bằng chứng `.jsonl` không được stage vào commit gắn tag; phát hiện khi kiểm `git show --stat` và bổ sung ngoại lệ `!docs/proof/**/*.jsonl`.
- **Nếu làm lại, đổi gì (hành động tiếp theo):**
  - Thiết lập quy tắc đọc hằng số từ `game.contract.json` và dùng `Fraction` cho đại lượng có ngưỡng ngay từ Phase 1 để giảm chi phí migrate khi gặp Change Request; dành thêm thời gian cuối Phase 4 để bổ sung âm thanh + 1 mở rộng (`burn` hoặc `leaderboard`).
