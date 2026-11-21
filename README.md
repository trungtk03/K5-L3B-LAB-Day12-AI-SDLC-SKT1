# Quán Ăn Chợ Nổi — Nhóm SKT1 (Day 12 · AI SDLC · Phase 3 · Contract v1.2)

> Game quản lý quán ăn 2D mang bản sắc miền Tây Nam Bộ: sáng Út Sen lặn bắt cá, hái rau trên sông Chín Khúc né Cá Sấu Năm Chèo; nguyên liệu có **độ tươi từng cá thể (`I1, I2, ...`)**, hao dần theo thời gian và bị ươn khi `< 30`; tối mở quán nhà bè 2 bếp / 4 bàn / 6 món (giá chốt theo độ tươi trung bình); cuối ngày vào Shop nâng cấp qua vòng 5 Ngày.

## Chạy sạch (≤ 3 lệnh)

```bash
# 1. Chơi trọn vòng 5 Ngày trên trình duyệt (Menu, Chuyển pha, Shop, Pause, HUD độ tươi)
python3 -m chonoi.live --mode day --days 5

# 2. Chạy headless trọn 1 Ngày theo Test Contract v1.2
python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day1.jsonl

# 3. Chạy toàn bộ kiểm thử tự động (77 ca: Contract v1.2, độ tươi, regression P1–P2, live)
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

> Trên Windows PowerShell: `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`

### Chạy hai buổi độc lập (nối qua file kho cá thể v1.2)

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
| `Esc` / `P` (`pause`) | Tạm dừng (dừng cả hao tươi) | Tạm dừng (dừng cả hao tươi) | Tạm dừng cả trong Shop |
| `R` | Chơi lại từ đầu (`live`) | Chơi lại từ đầu (`live`) | Nút Mua / Đóng Shop trên UI |

## Độ tươi, tính điểm & nâng cấp (Contract v1.2)

- **Kho cá thể & độ tươi:** Mỗi nguyên liệu vào giỏ được cấp `id` (`I1, I2, ...`) với `fresh = 100`, hao `-0.5/s` trong giỏ và `-0.25/s` trong kho quán (Shop và món chín không hao; `Pause` dừng hao). Khi `fresh < 30` nguyên liệu bị **ươn** (`spoiled`), vẫn chiếm chỗ và không dùng để nấu.
- **Giữ chỗ & giá theo độ tươi:** Khách gọi món giữ các cá thể chưa ươn tươi nhất theo `id`. Khi bắt đầu nấu, giá chốt `base_price = floor(giá niêm yết × trung bình fresh / 100)`. Nếu phục vụ khi kiên nhẫn `>= 50%`, boa `floor(base_price × 0.2)` và uy tín `+0.2` (kẹp `[0, 5]`); khách hết kiên nhẫn bỏ đi `-0.5` uy tín.
- **Điểm tổng:** `score = earned + 100 × floor(reputation)`. Nâng cấp Shop (`oxygen`: 200→45s, 400→60s; `hp`: 250→4 Máu, 500→5 Máu) chỉ trừ `money`, giữ `earned` và `score`, hiệu lực từ Ngày kế.

## Mở rộng & Sáng tạo của nhóm

- Nhóm SKT1 có 2 thành viên nên ở Phase 3 ưu tiên hoàn thiện chuẩn xác **100% Lõi Test Contract v1.2** (độ tươi chính xác bằng `Fraction`, kho cá thể, giữ lại 1 lần khi ươn, HUD độ tươi/ươn, 77/77 test xanh, tất định từng byte).

## Tài liệu nhóm

- Danh sách thành viên & thỏa thuận: [`TEAM.md`](TEAM.md)
- Kế hoạch, ADR & kiểm chứng: [`docs/plan/phase-3.md`](docs/plan/phase-3.md), [`docs/adr/0001-freshness-individual-inventory.md`](docs/adr/0001-freshness-individual-inventory.md), [`docs/verification/phase-3.md`](docs/verification/phase-3.md)
- Bằng chứng thực tế: [`docs/proof/phase-1/`](docs/proof/phase-1/), [`docs/proof/phase-2/`](docs/proof/phase-2/), [`docs/proof/phase-3/`](docs/proof/phase-3/)
- Hợp đồng v1.2 & kho mẫu: [`docs/contracts/README.md`](docs/contracts/README.md), [`docs/contracts/inventory.sample.json`](docs/contracts/inventory.sample.json)
- Lịch sử thay đổi (Breaking Changes): [`CHANGELOG.md`](CHANGELOG.md)
- Hướng dẫn agent & skills: [`AGENTS.md`](AGENTS.md), [`.agents/skills/`](.agents/skills/)
- Ghi chép nhóm: [`docs/clarify.md`](docs/clarify.md), [`docs/standup.md`](docs/standup.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`docs/retro.md`](docs/retro.md), [`docs/members/`](docs/members/)
