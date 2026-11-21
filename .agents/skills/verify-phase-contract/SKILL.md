---
name: verify-phase-contract
description: Kiểm tra tuân thủ Test Contract v1.0, tính tất định JSONL và bộ kiểm thử tự động trước khi gộp nhánh hoặc chốt phase cho dự án Quán Ăn Chợ Nổi (nhóm SKT1).
---

# Skill: verify-phase-contract

Dùng skill này trước khi commit/merge lên `main` hoặc trước khi gắn tag cuối phase.

## Các bước thực hiện

1. **Đọc hợp đồng hiện hành:**
   - Kiểm tra `game.contract.json` (khớp `team`, `team_size` với `TEAM.md`, không sửa nhầm `headless_cmd`).
   - Kiểm tra `docs/contracts/README.md` và `docs/contracts/inventory.sample.json`.
2. **Rà soát quy tắc lõi trong `chonoi/sim/`:**
   - Không còn thẻ `[PHẦN VIỆC CẦN LÀM: ...]` chưa xử lý trong phạm vi phase hiện tại.
   - Không dùng `random` toàn cục hay `time.*` trong logic mô phỏng; mọi ngẫu nhiên đi qua `self.rng.get(...)`.
   - Không hard-code số liệu đã có trong `game.contract.json`.
   - Mọi tập hợp xuất ra JSONL (`stock`, `items`, `nodes`, `fish`, `stoves`, `tables`, `customers`) đều được sắp thứ tự tất định.
3. **Chạy toàn bộ bộ kiểm thử tự động:**
   - Linux/macOS: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
   - Windows PowerShell: `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`
   - Xác nhận tất cả test (Contract hộp đen, Lát 1–4, E2E 2 tiến trình, live server, team check) đều `OK`.
4. **Báo cáo trung thực:**
   - Nếu có ca nào lỗi hoặc chưa xong, ghi rõ nguyên nhân và không bỏ qua test để làm xanh giả.
