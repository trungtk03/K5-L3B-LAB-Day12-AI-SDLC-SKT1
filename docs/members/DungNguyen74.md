# DungNguyen74 — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - Phase 1: Lập kế hoạch nhóm SKT1 (`TEAM.md`, `docs/plan/phase-1.md`), hoàn thiện Lát 1 & Lát 2 (`chonoi/sim/gather.py`, `tests/test_gather_lat1.py`, `tests/test_gather_lat2.py`) và dựng khung chú thích chi tiết cho Lát 3/4.
  - Phase 2 (phối hợp cùng `trungtk03`): Hoàn thiện `chonoi/sim/gather.py` v1.1 (6 nút hái gồm kèo nèo, 3 loài cá gồm cá kèo, 8 đàn đầu ca, cá bơi 1.5 m/s + phản xạ mép/góc + sinh cá 360·k, Cá Sấu Năm Chèo `M1`/`M2` với `patrol`/`chase`/`recoil`/hit/invuln/ngất) và bộ test `tests/test_gather_p2.py`.
- **Tôi đã review:** Kiểm tra hợp đồng v1.1, luồng `--mode day` và smoke tích hợp 2 tiến trình (`ca_keo` + `keo_neo`).
- **AI sai ở đâu và tôi phát hiện thế nào:** Ở Phase 1 test ban đầu thiếu tick cho thời gian giảm tốc ramp khi bơi lên mặt nước; ở Phase 2 rà kỹ quy tắc Cá Sấu hết `recoil` không được gây hit ngay trong cùng tick.
- **Điều tôi học được:** Giữ đúng thứ tự xử lý trong từng tick (bắt cá trước khi cá bơi, ngạt trước chạm quái) giúp mô phỏng tất định tuyệt đối.
