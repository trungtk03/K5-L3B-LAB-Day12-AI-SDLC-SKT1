# trungtk03 — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - **Phase 1 (`54f5b99`, `84291de`, `a154787`, `2918bfa`):** Hoàn thiện Lát 3–4 (`chonoi/sim/quan.py`), kiểm mâu thuẫn `scenario.py`, 12 ca test + E2E 2 tiến trình, hợp đồng, skills `.agents/skills/`, proof & tag `phase-1`.
  - **Phase 2 (`dd36bed`, `8bfcd86`, `5cc596a`, `1e37040`):** Nâng Contract v1.1, mở rộng `quan.py`, viết `day.py`, `shop.py`, `pause` cả 3 mode, Menu/HUD v1.1 & tag `phase-2`.
  - **Phase 3 (`30e2122`, `fcd59e4`, `0909d5b`, `017f659`):** Chốt ADR-0001, nâng kho cá thể `Fraction` v1.2, giữ chỗ theo `id`, giá theo độ tươi, HUD độ tươi/ươn & tag `phase-3`.
  - **Phase 4:** Triển khai `chonoi/bench.py`, `chonoi/soak.py`, 3 cảnh báo + tương phản cao, `tools/package_release.py`, `LICENSE`, Release `v1.0.0` & tag `phase-4`.
- **Tôi đã giúp & kiểm chéo:** Review Lát 1–2 của `DungNguyen74` (`eecd317`, `3a5de50`), pair hoàn thiện `gather.py` v1.1/v1.2 (`4e329aa`, `fcd59e4`) và giữ regression 82/82 test xanh.
- **AI sai ở đâu:** Quỹ đạo E2E lệch 3mm ngoài bán kính bàn `T1` và `.gitignore` từng bỏ sót file `.jsonl` proof — phát hiện qua test fail và `git show --stat`.
- **Bài học:** Khóa hợp đồng + ADR sớm và tự động hóa kiểm chứng giúp vượt Change Request lớn không vỡ `main`.
