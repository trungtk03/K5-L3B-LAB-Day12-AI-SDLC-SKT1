# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm SKT1

> Lịch sử cập nhật qua 4 phase:
> - Phase 1: 4 lát lõi v1.0, kiểm mâu thuẫn scenario, skills kiểm chứng & xuất proof.
> - Phase 2: Test Contract v1.1 (`--mode day`, `--days 1..5`, cá bơi/sinh, Cá Sấu M1/M2, 2 bếp/4 bàn/6 món, Shop, Pause, Menu/HUD).
> - Phase 3: Test Contract v1.2 (“Mùa Nước Nổi” — kho cá thể `{id, kind, fresh}`, hao tươi chính xác bằng `Fraction`, ngưỡng ươn `< 30`, giữ chỗ theo `id`, giá theo độ tươi, ADR-0001).
> - Phase 4: Test Contract v1.3 (`bench_cmd`, `soak_cmd`, 3 cảnh báo + chế độ tương phản cao, đóng gói phát hành `v1.0.0`, retro cuối buổi).

## Lệnh chạy thật
- Test (Linux/macOS/CI): `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Test (Windows PowerShell): `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`
- Headless 1 Ngày: `python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day1.jsonl`
- Benchmark có render `1280×720`: `python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json`
- Soak headless 10 Ngày: `python3 -m chonoi.soak --seed 7 --days 10 --out soak.json`
- Đóng gói bản phát hành: `python3 tools/package_release.py`
- Chơi trực tiếp trên trình duyệt: `python3 -m chonoi.live --mode day --days 5`

## Cấu trúc & quy ước (v1.3 / v1.0.0)
- Khung & CLI: `chonoi/{headless,bench,soak,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py`, `chonoi/web/index.html`, `tools/package_release.py`.
- Kho cá thể & độ tươi (`chonoi/inventory.py`): dùng `fractions.Fraction` (`gather`: `-1/120`/tick, `quan`: `-1/240`/tick), so ngưỡng `< 30` trước làm tròn, chốt `base_price = floor(price * avg_fresh / 100)`, từ chối file kho đếm bằng mã `2`.
- Vòng ngày (`chonoi/sim/day.py`): dùng chung `DaySim.item_ids` xuyên pha/Ngày; lặp `day_plan` D1–D5 ở Ngày 6–10+ (phục vụ Soak 10 Ngày).
- **Số liệu chỉ đọc từ `game.contract.json`**; ngẫu nhiên chỉ qua `Streams`; sắp danh sách thực thể bằng `sort_by_id` để tất định từng byte.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` khi chưa ghi ADR/báo cả nhóm và cập nhật test đồng bộ.
- Không đẩy lên nhánh chính khi bộ test chưa xanh hoàn toàn.

## Skills của nhóm (`.agents/skills/`)
- **`verify-phase-contract`** (`.agents/skills/verify-phase-contract/SKILL.md`): Kiểm tra tuân thủ Test Contract hiện hành, không hard-code số liệu, tính tất định từng byte và chạy full test suite trước khi gộp/gắn tag.
- **`generate-phase-proof`** (`.agents/skills/generate-phase-proof/SKILL.md`): Tạo bằng chứng chạy thật (unittest log, smoke, bench, soak, SHA-256) tại `docs/proof/phase-n/` và cập nhật `docs/verification/phase-n.md`.
