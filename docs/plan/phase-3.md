# Kế hoạch Phase 3 — Change Request “Mùa Nước Nổi” (35 phút · Contract v1.2)

## 1. Phân tích tác động (Impact Analysis)

| Module | File cần đổi | Test bị ảnh hưởng | Người phụ trách |
|---|---|---|---|
| **Manifest & Contract** | `game.contract.json`, `chonoi/contract.py`, `docs/contracts/README.md`, `docs/contracts/inventory.sample.json` | `tests/test_smoke_p1.py` | Nguyễn Hoàng Trung (`trungtk03`) |
| **Adapter Kho & Scenario** | `chonoi/inventory.py`, `chonoi/scenario.py` | `test_smoke_p1.py` (kho đếm phải trả mã 2, nâng fixture sang mảng cá thể) | Nguyễn Hoàng Trung (`trungtk03`) |
| **Lặn (`gather`)** | `chonoi/sim/gather.py` | `test_gather_lat1.py`, `test_gather_lat2.py`, `test_gather_p2.py`, thêm `test_freshness_p3.py` | Nguyễn Tuấn Dũng (`DungNguyen74`) |
| **Quán (`quan`)** | `chonoi/sim/quan.py` | `test_quan_lat3_lat4.py`, thêm `test_freshness_p3.py` | Nguyễn Hoàng Trung (`trungtk03`) |
| **Vòng Ngày & Shop (`day`, `shop`)** | `chonoi/sim/day.py`, `chonoi/sim/shop.py`, `chonoi/runner.py` | `test_day_p2.py`, thêm `test_freshness_p3.py` | Nguyễn Hoàng Trung (`trungtk03`) |
| **UI & HUD** | `chonoi/live.py`, `chonoi/web/index.html` | `test_live.py` | Nguyễn Hoàng Trung (`trungtk03`) |
| **QA, Proof & Docs** | `CHANGELOG.md`, `docs/adr/0001-*.md`, `docs/verification/phase-3.md`, `docs/proof/phase-3/` | Toàn bộ regression P1–P2 + bộ P3 mới | Cả hai (Integrator chốt tag) |

## 2. Quyết định đổi schema & thứ tự tích hợp giữ `main` luôn xanh
Xem chi tiết tại [ADR-0001](../adr/0001-freshness-individual-inventory.md):
1. Dùng `fractions.Fraction` cho tính toán độ tươi nội bộ (`gather`: `-1/120`/tick, `quan`: `-1/240`/tick) để so sánh ngưỡng `30` và tính `floor(price × avg_fresh / 100)` chính xác tuyệt đối không trôi dấu phẩy động.
2. Khôi phục phân số chính xác qua `Fraction(float(v)).limit_denominator(10**9)` khi đọc lại file `inventory.json` (ghi đủ độ chính xác float, sắp theo `id`).
3. Thứ tự tích hợp: **(1)** Lưu plan + ADR → **(2)** Nâng cấp đồng bộ `game.contract.json`, `contract.py`, `inventory.py`, `scenario.py`, `gather.py`, `quan.py`, `shop.py`, `day.py` sang v1.2 để `main` không bao giờ vỡ giữa chừng → **(3)** Cập nhật HUD `live.py`/`index.html` → **(4)** Cập nhật fixture P1–P2 + viết bộ test mới `test_freshness_p3.py` → **(5)** Chạy smoke ngưỡng 30, smoke bàn giao file, smoke `day`, regression toàn bộ, cập nhật `CHANGELOG.md` + proof + `docs/verification/phase-3.md` + tag `phase-3`.
