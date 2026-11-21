# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm SKT1

> Cập nhật theo từng phase (Phase 1: hoàn tất 4 lát lõi, kiểm mâu thuẫn scenario, skills kiểm chứng & xuất proof).

## Lệnh chạy thật
- Test (Linux/macOS/CI): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Test (Windows PowerShell): `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`
- Headless buổi sáng: `python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inventory-out kho.json --out gather.jsonl`
- Headless buổi tối: `python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --inventory kho.json --out quan.jsonl`
- Chơi thử trên trình duyệt: `python3 -m chonoi.live --mode gather|quan` (WASD/mũi tên, E, Space, R)

## Cấu trúc & quy ước
- Khung starter: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/`. Hạn chế sửa; mọi bổ sung kiểm lỗi mức luật (như `scenario.py` cho Phase 1) phải báo cả nhóm và ghi lại trong `docs/clarify.md`.
- Luật chơi của nhóm:
  - Buổi sáng (Lát 1 & 2): `chonoi/sim/gather.py` (`DungNguyen74`)
  - Buổi tối (Lát 3 & 4): `chonoi/sim/quan.py` (`trungtk03`)
- **Số liệu chỉ đọc từ `game.contract.json`**, không hard-code trong luật.
- Mọi số ngẫu nhiên đi qua `Streams` (`chonoi/rng.py`, ví dụ luồng `"customer"`); không dùng `random` toàn cục, không dùng đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`; danh sách món/nguyên liệu sắp theo khóa để JSONL tất định từng byte.
- Khi cập nhật uy tín float (`+0.2` / `-0.5`), làm tròn 6 chữ số sau khi kẹp `[reputation_min, reputation_max]` để tránh sai số dấu phẩy động làm lệch `math.floor(reputation)` trong công thức `score`.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` (khóa contract) khi chưa báo cả nhóm.
- Không đẩy lên nhánh chính khi bộ test chưa xanh hoàn toàn.
- Không bịa yêu cầu: chỗ mơ hồ ghi vào `docs/clarify.md` và thống nhất giữa PO & Integrator.
- Không sửa test cho xanh khi luật sai; phải sửa luật hoặc ghi lý do đổi test trong commit.

## Quy tắc làm việc với agent
- Mỗi agent phụ trách một lát/một việc rõ ràng; đọc `phase1.md` (hoặc PRD của phase hiện tại) và `docs/contracts/README.md` trước khi sửa code.
- Agent làm xong phải chạy toàn bộ test, cập nhật `docs/ai-usage-log.md` và xuất bằng chứng vào `docs/proof/phase-n/`; thành viên nhóm đọc lại diff trước khi gộp và gắn tag.
- Sáng tạo thêm được khuyến khích sau khi lõi đúng, nhưng phải tắt ở headless.

## Skills của nhóm (`.agents/skills/`)
- **`verify-phase-contract`** (`.agents/skills/verify-phase-contract/SKILL.md`): Dùng trước khi gộp code hoặc chốt phase — kiểm tra toàn bộ Test Contract v1.0, kiểm không hard-code số liệu, kiểm tính tất định từng byte và chạy full test suite.
- **`generate-phase-proof`** (`.agents/skills/generate-phase-proof/SKILL.md`): Dùng ở cuối mỗi phase trước khi gắn tag — chạy lại bộ test thật, chạy smoke/E2E 2 tiến trình (`gather` → `inventory.json` → `quan`), kiểm SHA-256 tính tất định và lưu bằng chứng vào `docs/proof/phase-n/`.
