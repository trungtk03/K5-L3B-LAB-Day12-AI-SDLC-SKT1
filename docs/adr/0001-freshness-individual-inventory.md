# ADR-0001: Chuyển đổi kho đếm sang kho cá thể có độ tươi (Contract v1.2)

- **Ngày:** 2026-11-21
- **Trạng thái:** Đã chốt (Phase 3)
- **Người quyết định:** Nguyễn Hoàng Trung (`trungtk03` — Integrator) & Nguyễn Tuấn Dũng (`DungNguyen74` — PO/QA)

## Bối cảnh
Change Request TICKET-03 ("Mùa Nước Nổi") thay đổi mô hình kho từ bản đồ đếm theo loại (`{"items": {"ca_loc": 1}}`) sang mảng cá thể mang định danh và độ tươi (`{"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]}`), đồng thời áp dụng hao tươi từng tick (`-0.5/s` ở giỏ, `-0.25/s` ở kho quán), ngưỡng ươn `< 30`, giữ chỗ theo `id` cá thể và tính giá món theo độ tươi trung bình.

## Quyết định
1. **Số học chính xác bằng `fractions.Fraction`:**
   - Mọi cá thể lưu độ tươi nội bộ dưới dạng `Fraction` (`gather`: `-Fraction(1, 120)`/tick; `quan`: `-Fraction(1, 240)`/tick).
   - So ngưỡng ươn `< Fraction(30)` trước khi làm tròn để phát `spoiled` chính xác đúng tick biên.
   - Tính `base_price = math.floor(Fraction(price) * avg_fresh / Fraction(100))` không bị lỗi làm tròn IEEE-754.
   - Khi đọc lại từ JSON/file kho: dùng `Fraction(float(v)).limit_denominator(10**9)` khôi phục chính xác cả bội `1/240` lẫn số thập phân fixture.
2. **Cấp phát `id` cá thể xuyên suốt (`I1, I2, ...`):**
   - `DaySim` giữ chung một bộ đếm `item_ids = IdAllocator()` xuyên qua mọi pha (`gather → quan → shop`) và mọi Ngày (`D1..D5`).
   - Ngày 1 giữ nguyên `id` trong `scenario.gather.hold` (và `reserve` vào `item_ids`); các Ngày tiếp theo cấp `id` mới theo thứ tự mảng với `kind` và `fresh` ban đầu.
3. **Từ chối kho đếm cũ (Breaking Change v1.2):**
   - `chonoi/inventory.py` và `chonoi/scenario.py` bắt buộc `items` / `hold` / `stock` là mảng cá thể `{id, kind, fresh}` hợp lệ; mọi file kho đếm v1.0/v1.1 trả mã thoát `2` trước khi ghi đầu ra.

## Hệ quả & kế hoạch kiểm soát
- Các test Phase 1 & Phase 2 dùng fixture kho đếm cần chuyển sang mảng cá thể và ghi rõ lý do trong `CHANGELOG.md` và `docs/verification/phase-3.md`.
- `docs/contracts/inventory.sample.json` và HUD (`chonoi/web/index.html`) cập nhật đồng bộ theo schema v1.2.
