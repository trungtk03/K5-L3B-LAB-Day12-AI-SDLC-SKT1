# trungtk03 — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - Phase 1: Hoàn thiện Lát 3 & Lát 4 (`chonoi/sim/quan.py`), kiểm mâu thuẫn scenario (`chonoi/scenario.py`), 12 ca test + E2E 2 tiến trình, tài liệu DoD, skills `.agents/skills/`, proof Phase 1 và tag `phase-1`.
  - Phase 2: Nâng cấp toàn bộ hệ thống lên Test Contract v1.1 (`game.contract.json`, `contract/inventory/inputs/scenario/headless`), mở rộng `quan.py` (2 bếp/4 bàn/6 món + lọc `day_plan`), triển khai `shop.py`, `day.py`, `pause` cả 3 mode trong `runner.py`, Menu/Chuyển pha/Shop/Pause/HUD v1.1 (`live.py`, `web/index.html`), phối hợp hoàn thiện `gather.py` v1.1, xuất bộ proof 70/70 test xanh và chốt tag `phase-2`.
- **Tôi đã review:** Đối chiếu toàn bộ số chuẩn TICKET-02, rà regression P1 và cập nhật có giải trình 3 assertion thay đổi theo v1.1.
- **AI sai ở đâu và tôi phát hiện thế nào:** Phase 1 từng lệch 3mm ngoài bán kính bàn `T1` trong test E2E và phát hiện rủi ro sai số float khi cộng uy tín `0.2`; Phase 2 rà soát kỹ thứ tự `buy` trước `shop_done` ở bước cuối và sao `upgrades → active_upgrades` chỉ khi sang Ngày mới.
- **Điều tôi học được:** Khóa manifest và thứ tự xử lý mỗi tick ngay từ đầu phase giúp ghép nhiều pha `gather → quan → shop` qua nhiều Ngày cực kỳ ổn định.
