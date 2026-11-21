# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm SKT1

> Cập nhật theo từng phase:
> - Phase 1: hoàn tất 4 lát lõi v1.0, kiểm mâu thuẫn scenario, skills kiểm chứng & xuất proof.
> - Phase 2: nâng cấp Test Contract v1.1 (`--mode day`, `--days 1..5`, cá bơi/sinh, Cá Sấu M1/M2, 2 bếp/4 bàn/6 món, Shop, Pause, Menu/HUD).

## Lệnh chạy thật
- Test (Linux/macOS/CI): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Test (Windows PowerShell): `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`
- Headless 1 Ngày (v1.1): `python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day1.jsonl`
- Headless buổi sáng/tối độc lập:
  - `python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inventory-out kho.json --out gather.jsonl`
  - `python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --inventory kho.json --out quan.jsonl`
- Chơi thử trên trình duyệt: `python3 -m chonoi.live --mode day --days 5` (hoặc `--mode gather|quan`)

## Cấu trúc & quy ước (v1.1)
- Khung hệ thống: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/index.html`.
- Luật chơi của nhóm:
  - Buổi sáng (`chonoi/sim/gather.py`): 6 nút hái, 3 loài cá, cá bơi + phản xạ mép + sinh theo lịch, Cá Sấu Năm Chèo `M1`/`M2`.
  - Buổi tối (`chonoi/sim/quan.py`): 2 bếp (`B1–B2`), 4 bàn (`T1–T4`), 6 món, lọc thực đơn theo `day_plan` khi chạy `day`.
  - Vòng ngày & Cửa hàng (`chonoi/sim/day.py`, `chonoi/sim/shop.py`): `gather → quan → shop` qua 1..5 Ngày, `upgrades → active_upgrades` áp dụng từ Ngày kế.
  - Tạm dừng (`chonoi/runner.py`): xét cạnh `pause` đầu bước cho cả 3 mode (kể cả Shop), đóng băng `sim_tick`/`phase_tick`/timer.
- **Số liệu chỉ đọc từ `game.contract.json`**, không hard-code trong luật và cả trong test mới.
- Mọi số ngẫu nhiên đi qua `Streams` (`fish_spawn`, `fish_move`, `customer`); không dùng `random` toàn cục hay đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`; sắp khóa dict trước khi xuất JSONL để tất định từng byte.
- Khi cập nhật uy tín float (`+0.2` / `-0.5`), làm tròn 6 chữ số sau khi kẹp `[reputation_min, reputation_max]` để tránh lệch `math.floor(reputation)`.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` khi chưa báo cả nhóm và cập nhật test đồng bộ.
- Không đẩy lên nhánh chính khi bộ test chưa xanh hoàn toàn.
- Không bịa yêu cầu: chỗ mơ hồ ghi vào `docs/clarify.md` và thống nhất giữa PO & Integrator.
- Khi luật phase mới làm đổi kỳ vọng test cũ, ghi rõ lý do trong commit và `docs/verification/phase-n.md`.

## Skills của nhóm (`.agents/skills/`)
- **`verify-phase-contract`** (`.agents/skills/verify-phase-contract/SKILL.md`): Kiểm tra tuân thủ Test Contract hiện hành, không hard-code số liệu, tính tất định từng byte và chạy full test suite trước khi gộp/gắn tag.
- **`generate-phase-proof`** (`.agents/skills/generate-phase-proof/SKILL.md`): Tạo bằng chứng chạy thật (unittest log, smoke tích hợp 2 tiến trình, smoke `day`, kiểm SHA-256 & hiệu năng) tại `docs/proof/phase-n/` và cập nhật `docs/verification/phase-n.md`.
