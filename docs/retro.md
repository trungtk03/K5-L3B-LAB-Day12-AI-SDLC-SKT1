# Retro nhóm

## Phase 2 (nhanh)
- **Điều tốt:**
  - Chốt sớm nền Test Contract v1.1 (`game.contract.json`, `contract.py`, `inventory.py`, `inputs.py`, `scenario.py`, `headless.py`) giúp các lát `gather` (cá bơi/sinh, Cá Sấu) và `quan`/`day`/`shop` tích hợp mượt, 15 ca test Phase 2 xanh ngay lần chạy đầu.
  - Hiệu năng headless một Ngày đầy đủ 22.200 tick chỉ ~1.0s (vượt xa ngưỡng ≤ 20s) và tất định 100% từng byte trên cả 3 mode.
- **Điều tệ:**
  - Quy mô nhóm chỉ có 2 người nên áp lực thời gian giữa việc code lõi + giao diện Menu/HUD + xuất bằng chứng khá gấp, chưa kịp làm thêm mở rộng (như `burn` hoặc `vendor`).
  - Một số test Phase 1 hard-code số lượng cũ (`fish=6`, `stoves=1`) phải rà và cập nhật lại khi đổi sang số chuẩn v1.1.
- **1 hành động cho Phase 3 (người nhận: `trungtk03` & `DungNguyen74`):**
  - Mọi test mới từ Phase 3 trở đi luôn đọc hằng số từ `game.contract.json` (không hard-code số lượng bàn/bếp/cá), đồng thời giữ sẵn kịch bản benchmark & smoke tự động để xuất proof trong 1 lệnh duy nhất trước mốc bàn giao 10 phút.

## Phase 3 (nhanh — rút kinh nghiệm đổi schema kho v1.2)
- **Điều tốt:** Phân tích tác động và chốt ADR-0001 (dùng `fractions.Fraction` + helper `items_v12()`) ngay 7 phút đầu giúp chuyển đổi toàn bộ 4 module sim + 77 ca test sang kho cá thể không phát sinh lỗi làm tròn hay vỡ nhánh giữa chừng.
- **Bài học từ breaking change:** Tập trung toàn bộ quy ước đọc/ghi/validate cá thể vào một module duy nhất (`chonoi/inventory.py`) giúp các module sim (`gather`, `quan`, `shop`, `day`) chỉ phụ thuộc một nguồn chân lý.

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
