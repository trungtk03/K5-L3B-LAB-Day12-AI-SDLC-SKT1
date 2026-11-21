# trungtk03 — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm:**
  - Hoàn thiện Lát 3 & Lát 4 cho buổi tối (`chonoi/sim/quan.py`) gồm lịch khách, giữ chỗ nguyên liệu, kiên nhẫn, nấu/bưng/phục vụ, tính boa, uy tín và đóng ca `quan_end`, cùng kiểm mâu thuẫn scenario mức luật (`chonoi/scenario.py`).
  - Viết bộ kiểm thử Lát 3/4 và E2E 2 tiến trình (`tests/test_quan_lat3_lat4.py`), hoàn thiện hợp đồng tích hợp (`docs/contracts/README.md`), `README.md`, `AGENTS.md`, 2 skill nhóm trong `.agents/skills/`, xuất bằng chứng thực tế (`docs/proof/phase-1/`), hoàn thiện `docs/verification/phase-1.md` và gắn tag `phase-1`.
- **Tôi đã review:** Rà soát cài đặt Lát 1 & Lát 2 của `DungNguyen74` (`chonoi/sim/gather.py`, `tests/test_gather_lat1.py`, `tests/test_gather_lat2.py`) ở commit `eecd317` và `3a5de50` — chạy lại toàn bộ 10 ca test gather đều xanh.
- **AI sai ở đâu và tôi phát hiện thế nào:** Khi chạy test E2E đầu tiên, bước di chuyển từ bếp `B1` về bàn `T1` bị dừng cách bàn `1.503m` (lệch 3mm ngoài `interact_radius = 1.5m`) nên không phát `served`; ngoài ra phát hiện rủi ro sai số float khi cộng dồn `0.2` uy tín ảnh hưởng `floor(reputation)`. Đã sửa và xác minh bằng test tự động.
- **Điều tôi học được:** Chia 4 lát rõ ràng và khóa hợp đồng sớm giúp 2 người làm song song rồi ghép 2 tiến trình qua `inventory.json` rất mượt.
