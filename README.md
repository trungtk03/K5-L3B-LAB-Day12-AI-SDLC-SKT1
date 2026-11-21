# Quán Ăn Chợ Nổi — Nhóm SKT1 (Day 12 · AI SDLC)

> Game quản lý quán ăn 2D mang bản sắc miền Tây Nam Bộ: buổi sáng Út Sen lặn bắt cá và hái rau trên sông Chín Khúc (`gather`); buổi tối mở quán nhà bè nấu và phục vụ khách (`quan`), nối nhau qua file kho `inventory.json`.

## Chạy sạch (≤ 3 lệnh)

```bash
# 1. Chơi thử trực tiếp trên trình duyệt (buổi sáng; thêm --inventory-out kho.json để xuất kho)
python3 -m chonoi.live --mode gather --inventory-out kho.json

# 2. Mở quán buổi tối trên trình duyệt từ file kho buổi sáng
python3 -m chonoi.live --mode quan --inventory kho.json

# 3. Chạy kiểm thử tự động (Test Contract hộp đen + unit/E2E của nhóm)
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```

> Trên Windows PowerShell: `$env:PYTHONPATH="tests;."; python -m unittest discover -s tests -v`

### Chạy headless (Test Contract v1.0)

```bash
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inventory-out kho.json --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --inventory kho.json --out quan.jsonl
```

## Điều khiển

| Phím | Buổi sáng (`gather`) | Buổi tối (`quan`) |
|---|---|---|
| `W A S D` / Phím mũi tên | Bơi ngang (`x`) và lặn/nổi (`d`) | Đi lại trong quán (`x`, `z`) |
| `E` (`interact`) | Cập bến (trong vùng bến) hoặc hái rau ở mặt nước | Nấu món (bếp rảnh), bưng món (bếp chín), phục vụ bàn |
| `Space` (`catch`) | Bắt đàn cá khi đang lặn dưới nước | — |
| `R` | Chơi lại từ đầu (chế độ `live`) | Chơi lại từ đầu (chế độ `live`) |

## Cách tính điểm

- **Tiền món (`base_price`):** Cá lóc nướng trui `60` (`ca_loc × 1`, nấu 6s), Gỏi bông súng `40` (`bong_sung × 2`, nấu 4s), Lẩu cá linh bông điên điển `120` (`ca_linh × 3 + bong_dien_dien × 1`, nấu 10s).
- **Tiền boa (`tip`):** Nếu phục vụ khi kiên nhẫn còn `>= 50%` (`tip_min_patience_ratio = 0.5`), `tip = floor(base_price × 0.2)` và tăng uy tín `+0.2` (kẹp trong `[0, 5]`). Khách hết kiên nhẫn bỏ đi làm giảm uy tín `-0.5`.
- **Điểm tổng (`score`):** `score = earned + 100 × floor(reputation)` (mọi số liệu đọc từ [`game.contract.json`](game.contract.json)).

## Sáng tạo của nhóm

- Phase 1 tập trung hoàn thiện chuẩn xác 100% lõi Test Contract v1.0 (4 lát `gather` + `quan`, kiểm mâu thuẫn scenario mức luật mã thoát 2, tính tất định từng byte và E2E 2 tiến trình) trước khi mở rộng sáng tạo ở các phase tiếp theo.

## Cấu trúc & tài liệu nhóm

- Danh sách thành viên & thỏa thuận: [`TEAM.md`](TEAM.md)
- Kế hoạch & kiểm chứng Phase 1: [`docs/plan/phase-1.md`](docs/plan/phase-1.md), [`docs/verification/phase-1.md`](docs/verification/phase-1.md), [`docs/proof/phase-1/`](docs/proof/phase-1/)
- Hợp đồng tích hợp & kho mẫu: [`docs/contracts/README.md`](docs/contracts/README.md), [`docs/contracts/inventory.sample.json`](docs/contracts/inventory.sample.json)
- Hướng dẫn agent & skills: [`AGENTS.md`](AGENTS.md), [`.agents/skills/`](.agents/skills/)
- Ghi chép nhóm: [`docs/clarify.md`](docs/clarify.md), [`docs/standup.md`](docs/standup.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`docs/retro.md`](docs/retro.md), [`docs/members/`](docs/members/)
- Chi tiết khung starter Python: [`docs/STARTER.md`](docs/STARTER.md)
