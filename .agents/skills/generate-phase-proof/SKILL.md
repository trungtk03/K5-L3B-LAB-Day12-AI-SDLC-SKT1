---
name: generate-phase-proof
description: Tạo bộ bằng chứng chạy thực tế (unittest log, E2E 2 tiến trình gather -> inventory -> quan, kiểm băm SHA-256 tất định) tại docs/proof/phase-n/ và cập nhật ma trận truy vết docs/verification/phase-n.md.
---

# Skill: generate-phase-proof

Dùng skill này khi chuẩn bị bàn giao cuối phase và gắn tag `phase-n`.

## Đầu ra bắt buộc trong `docs/proof/phase-<n>/`

1. **`unittest.log`**: Ghi nguyên văn kết quả chạy `unittest discover -s tests -v` ở commit chuẩn bị gắn tag.
2. **Bằng chứng E2E 2 tiến trình (`e2e_gather.jsonl`, `e2e_inventory.json`, `e2e_quan.jsonl`, `e2e_summary.txt`)**:
   - Chạy tiến trình 1 (`--mode gather --inventory-out docs/proof/phase-<n>/e2e_inventory.json --out docs/proof/phase-<n>/e2e_gather.jsonl`) có bắt cá/hái rau và cập bến.
   - Chạy tiến trình 2 (`--mode quan --inventory docs/proof/phase-<n>/e2e_inventory.json --out docs/proof/phase-<n>/e2e_quan.jsonl`) phục vụ ít nhất 1 khách ăn xong trả tiền.
   - Ghi tóm tắt các sự kiện chính và điểm cuối vào `e2e_summary.txt`.
3. **`determinism_check.txt`**:
   - Chạy mỗi mode (`gather` và `quan`) 2 lần độc lập với cùng `--seed` và so sánh SHA-256 từng byte phải trùng khớp 100%.
4. **Cập nhật `docs/verification/phase-<n>.md`**:
   - Điền bảng ma trận truy vết (AC → cách kiểm chứng → link file trong `docs/proof/phase-<n>/` → kết quả trung thực) và mục đánh giá ngắn.
