# DungNguyen74 — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - **Phase 1 (`b101ee2`, `eecd317`, `3a5de50`):** Lập kế hoạch nhóm SKT1 (`TEAM.md`, `docs/plan/phase-1.md`), hoàn thiện Lát 1 & Lát 2 (`chonoi/sim/gather.py`: oxy, ngạt, Máu, ngất LIFO, hái rau, bắt cá), viết 10 ca test (`test_gather_lat1.py`, `test_gather_lat2.py`) và khung chú thích chi tiết Lát 3/4 trong `quan.py`.
  - **Phase 2–4 (pair cùng `trungtk03`, `Co-authored-by` ở `4e329aa`, `e34d5be`, `fcd59e4`, `e2f2939`):** Hoàn thiện `gather.py` v1.1/v1.2 (cá bơi phản xạ mép, sinh cá `360·k`, Cá Sấu `M1`/`M2`, hao tươi & `spoiled` theo `id`), bộ kiểm thử `test_gather_p2.py`, `test_freshness_p3.py` và rà QA cho `bench`/`soak` ở Phase 4.
- **Tôi đã giúp & kiểm chéo:** Chia rõ phần việc Lát 3/4 cho nhóm trưởng bằng khung chú thích cụ thể, kiểm chéo hợp đồng v1.0 → v1.3 và kiểm duyệt bộ regression 82/82 ca xanh.
- **AI sai ở đâu:** Ở Phase 1 test ban đầu thiếu tick cho thời gian giảm tốc ramp khi bơi lên mặt nước; đã phát hiện qua test fail và bổ sung đủ tick.
- **Bài học:** Tuân thủ đúng thứ tự xử lý trong từng tick (hao tươi đầu bước, bắt cá trước khi cá bơi, ngạt trước chạm quái) quyết định tính tất định của toàn hệ thống.
