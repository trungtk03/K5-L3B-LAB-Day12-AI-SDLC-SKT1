# Quán Ăn Chợ Nổi — Nhóm SKT1 (Day 12 · AI SDLC · Phase 2 · Contract v1.1)

> Game quản lý quán ăn 2D mang bản sắc miền Tây Nam Bộ: sáng Út Sen lặn bắt cá (cá linh, cá lóc, cá kèo) né Cá Sấu Năm Chèo và hái rau (điên điển, bông súng, kèo nèo) theo kế hoạch Má Tư; tối mở quán nhà bè 2 bếp / 4 bàn / 6 món; cuối ngày vào Shop nâng cấp Bình oxy & Áo phao qua vòng 5 Ngày.

## Chạy sạch (≤ 3 lệnh)

```bash
# 1. Chơi trọn vòng 5 Ngày trên trình duyệt (Menu, Chuyển pha, Shop, Pause, HUD v1.1)
python3 -m chonoi.live --mode day --days 5

# 2. Chạy headless trọn 1 Ngày theo Test Contract v1.1
python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day1.jsonl

# 3. Chạy toàn bộ kiểm thử tự động (70 ca: Contract v1.1, regression P1, P2, live)
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

> Trên Windows PowerShell: `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`

### Chạy hai buổi độc lập (nối qua file kho)

```bash
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inventory-out kho.json --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --inventory kho.json --out quan.jsonl
```

## Điều khiển

| Phím | Buổi sáng (`gather`) | Buổi tối (`quan`) | Chung / Shop |
|---|---|---|---|
| `W A S D` / Phím mũi tên | Bơi ngang (`x`) và lặn/nổi (`d`) | Đi lại trong quán (`x`, `z`) | — |
| `E` (`interact`) | Cập bến (vùng bến) hoặc hái rau mặt nước | Nấu món (bếp rảnh), bưng món (bếp chín), phục vụ bàn | — |
| `Space` (`catch`) | Bắt đàn cá dưới nước | — | — |
| `Esc` / `P` (`pause`) | Tạm dừng / Tiếp tục | Tạm dừng / Tiếp tục | Tạm dừng cả trong Shop |
| `R` | Chơi lại từ đầu (`live`) | Chơi lại từ đầu (`live`) | Nút Mua / Đóng Shop trên UI |

## Cách tính điểm & nâng cấp

- **6 món ăn (`game.contract.json` v1.1):** Cá lóc nướng trui `60` (`ca_loc ×1`, 6s), Gỏi bông súng `40` (`bong_sung ×2`, 4s), Lẩu cá linh bông điên điển `120` (`ca_linh ×3 + bong_dien_dien ×1`, 10s), Canh chua cá lóc `90` (`ca_loc ×1 + bong_dien_dien ×1`, 8s), Cá kèo nướng muối ớt `70` (`ca_keo ×2`, 6s), Lẩu mắm miền Tây `200` (`ca_linh ×2 + ca_keo ×1 + keo_neo ×1 + bong_dien_dien ×1`, 12s).
- **Boa & Uy tín:** Phục vụ khi kiên nhẫn còn `>= 50%` → `tip = floor(price × 0.2)` và uy tín `+0.2` (kẹp `[0, 5]`); khách hết kiên nhẫn bỏ đi `-0.5` uy tín.
- **Điểm tổng:** `score = earned + 100 × floor(reputation)`. Mua nâng cấp trong Shop (`oxygen`: 200→45s, 400→60s; `hp`: 250→4 Máu, 500→5 Máu) chỉ trừ vào `money`, giữ nguyên `earned` và `score`, hiệu lực từ Ngày kế tiếp.

## Mở rộng & Sáng tạo của nhóm

- Nhóm SKT1 gồm 2 thành viên nên ở Phase 2 tập trung hoàn thiện chuẩn xác **100% Lõi Test Contract v1.1** (chưa bật extension ở `game.contract.json`), đảm bảo 70/70 test xanh, tất định từng byte và hiệu năng ~1s cho trọn 1 Ngày 22.200 tick.

## Tài liệu nhóm

- Danh sách thành viên & thỏa thuận: [`TEAM.md`](TEAM.md)
- Kế hoạch & kiểm chứng Phase 1–2: [`docs/plan/phase-1.md`](docs/plan/phase-1.md), [`docs/plan/phase-2.md`](docs/plan/phase-2.md), [`docs/verification/phase-1.md`](docs/verification/phase-1.md), [`docs/verification/phase-2.md`](docs/verification/phase-2.md)
- Bằng chứng thực tế: [`docs/proof/phase-1/`](docs/proof/phase-1/), [`docs/proof/phase-2/`](docs/proof/phase-2/)
- Hợp đồng v1.1 & kho mẫu: [`docs/contracts/README.md`](docs/contracts/README.md), [`docs/contracts/inventory.sample.json`](docs/contracts/inventory.sample.json)
- Hướng dẫn agent & skills: [`AGENTS.md`](AGENTS.md), [`.agents/skills/`](.agents/skills/)
- Ghi chép nhóm: [`docs/clarify.md`](docs/clarify.md), [`docs/standup.md`](docs/standup.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`docs/retro.md`](docs/retro.md), [`docs/members/`](docs/members/)
