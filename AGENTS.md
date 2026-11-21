# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm SKT1

> Cập nhật theo từng phase:
> - Phase 1: 4 lát lõi v1.0, kiểm mâu thuẫn scenario, skills kiểm chứng & xuất proof.
> - Phase 2: Test Contract v1.1 (`--mode day`, `--days 1..5`, cá bơi/sinh, Cá Sấu M1/M2, 2 bếp/4 bàn/6 món, Shop, Pause, Menu/HUD).
> - Phase 3: Test Contract v1.2 (“Mùa Nước Nổi” — kho cá thể `{id, kind, fresh}`, hao tươi chính xác bằng `Fraction`, ngưỡng ươn `< 30`, giữ chỗ theo `id`, giá theo độ tươi, ADR-0001).

## Lệnh chạy thật
- Test (Linux/macOS/CI): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Test (Windows PowerShell): `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`
- Headless 1 Ngày (v1.2): `python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day1.jsonl`
- Headless buổi sáng/tối độc lập (kho cá thể v1.2):
  - `python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inventory-out kho.json --out gather.jsonl`
  - `python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --inventory kho.json --out quan.jsonl`
- Chơi thử trên trình duyệt: `python3 -m chonoi.live --mode day --days 5` (hoặc `--mode gather|quan`)

## Cấu trúc & quy ước (v1.2)
- Khung hệ thống: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/index.html`.
- Kho cá thể & độ tươi (`chonoi/inventory.py`):
  - Dùng `fractions.Fraction` cho mọi phép trừ độ tươi (`gather`: `-1/120`/tick, `quan`: `-1/240`/tick), so ngưỡng `< 30` trước khi làm tròn và tính `base_price = floor(price * avg_fresh / 100)`.
  - Mọi file kho đếm v1.0/v1.1 phải trả mã thoát `2`.
  - Trong `day`, dùng chung một `IdAllocator` (`DaySim.item_ids`) để cấp `I1, I2, ...` tăng liên tục xuyên pha và Ngày.
- Luật chơi:
  - Buổi sáng (`chonoi/sim/gather.py`): hao tươi đầu bước → bơi/oxy/ngạt → Cá Sấu `M1`/`M2` → bến/hái → bắt cá → hết giờ → cá bơi/sinh.
  - Buổi tối (`chonoi/sim/quan.py`): đồng hồ/timer → hao tươi & phát `spoiled` theo `id` → nhả & thử giữ lại 1 lần cho đơn bị ươn (hoặc `unfulfillable`) → món chín → di chuyển/tương tác → thanh toán/kiên nhẫn/đóng ca → khách mới.
  - Vòng ngày & Cửa hàng (`chonoi/sim/day.py`, `chonoi/sim/shop.py`): bàn giao kho cá thể chính xác trong bộ nhớ; Shop không hao tươi.
- **Số liệu chỉ đọc từ `game.contract.json`**, không hard-code trong luật và test mới.
- Mọi số ngẫu nhiên đi qua `Streams` (`fish_spawn`, `fish_move`, `customer`); không dùng `random` toàn cục hay đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`; `cook_started.items` sắp theo `(kind, id)` để tất định từng byte.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` khi chưa ghi ADR/báo cả nhóm và cập nhật test đồng bộ.
- Không đẩy lên nhánh chính khi bộ test chưa xanh hoàn toàn.
- Khi luật phase mới làm đổi kỳ vọng test cũ, ghi rõ lý do trong `CHANGELOG.md`, commit và `docs/verification/phase-n.md`.

## Skills của nhóm (`.agents/skills/`)
- **`verify-phase-contract`** (`.agents/skills/verify-phase-contract/SKILL.md`): Kiểm tra tuân thủ Test Contract hiện hành, không hard-code số liệu, tính tất định từng byte và chạy full test suite trước khi gộp/gắn tag.
- **`generate-phase-proof`** (`.agents/skills/generate-phase-proof/SKILL.md`): Tạo bằng chứng chạy thật (unittest log, smoke ngưỡng/bàn giao kho/day, kiểm SHA-256 & hiệu năng) tại `docs/proof/phase-n/` và cập nhật `docs/verification/phase-n.md`.
