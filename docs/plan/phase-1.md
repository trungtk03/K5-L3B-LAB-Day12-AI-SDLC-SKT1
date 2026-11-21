# Kế hoạch Phase 1 (≤ 1 trang)

## Mục tiêu
Hoàn thành 4 lát lõi của Phase 1 theo PRD-0 và Test Contract v1.0 trong 60 phút:
1. Buổi sáng (`gather`): Bơi, oxy, ngạt, máu, ngất, hái cây, bắt cá, cập bến xuất kho.
2. Buổi tối (`quan`): Khách theo lịch, giữ chỗ nguyên liệu, kiên nhẫn, bếp nấu, phục vụ, thanh toán/boa, uy tín, kết ca.
3. Liên thông hai tiến trình qua file kho (`inventory.json`), toàn bộ test xanh và lưu bằng chứng tại `docs/proof/phase-1/`.

## Việc / người / phụ thuộc

| Lát | Việc | Người làm | Phụ thuộc |
|---|---|---|---|
| Lát 1 | Bơi, oxy, ngạt, Máu, ngất, sự kiện dive/surface | Nguyễn Tuấn Dũng (`DungNguyen74`) | Khung starter `gather.py` |
| Lát 2 | Hái nút, bắt cá, sức chứa giỏ, xuất kho bến | Nguyễn Tuấn Dũng (`DungNguyen74`) | Lát 1 |
| Lát 3 | Khách theo lịch, kiểm tra nguyên liệu, giữ chỗ, kiên nhẫn, rời quán | Nhóm trưởng (`trungtk03`) | Khung starter `quan.py` |
| Lát 4 | Bếp nấu, lấy món lên tay, phục vụ bàn, trả tiền, boa, uy tín, hết ca | Nhóm trưởng (`trungtk03`) | Lát 3 |
| QA & E2E | Bộ test từng lát + test hộp đen 2 tiến trình, ma trận truy vết | Cả hai | Lát 1, 2, 3, 4 |

## Rủi ro & Giải pháp
1. **Sai lệch thứ tự tick/sự kiện:** Tuân thủ đúng thứ tự trong PRD mục F (cập bến trước hái; bếp trước bàn; check mép; timer).
2. **Hard-code số liệu:** Mọi hằng số lấy từ `game.contract.json` qua `self.t` và `tuning`.
3. **Mất tính tất định:** Không dùng `random` ngẫu nhiên, chỉ dùng `self.rng.get(...)`.
4. **Hết giờ phase:** Thường xuyên chạy smoke test sau từng lát, chốt commit liên tục và gắn tag `phase-1` trước mốc 1:00.
