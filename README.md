# Quán Ăn Chợ Nổi — v1.0.0 (Nhóm SKT1 · Test Contract v1.3)

> Game quản lý quán ăn 2D mang bản sắc miền Tây Nam Bộ: sáng Út Sen lặn bắt cá, hái rau trên sông Chín Khúc né Cá Sấu Năm Chèo, theo dõi độ tươi từng nguyên liệu (`I1, I2, ...`); tối mở quán nhà bè 2 bếp / 4 bàn / 6 món theo kế hoạch Má Tư; cuối ngày vào Shop nâng cấp Bình oxy & Áo phao qua vòng 5 Ngày.

## Yêu cầu môi trường
- **Python 3.10+** (100% thư viện chuẩn, **không cần `pip install`** bất kỳ gói ngoài nào).
- **Trình duyệt web hiện đại** (Chrome / Firefox / Safari / Edge) để chơi chế độ giao diện (`chonoi.live`).
- Chạy nguyên bản trên **macOS, Linux và Windows**.

## Chạy sạch bản có giao diện (≤ 3 lệnh trên macOS / Linux)

```bash
git clone https://github.com/trungtk03/K5-L3B-LAB-Day12-AI-SDLC-SKT1.git
cd K5-L3B-LAB-Day12-AI-SDLC-SKT1
python3 -m chonoi.live --mode day --days 5
```

> Mở địa chỉ `http://127.0.0.1:8000/` trên trình duyệt. Nếu dùng gói phát hành `quan-an-cho-noi-v1.0.0.zip` từ GitHub Release `v1.0.0`, giải nén và chạy `./run.sh` (macOS/Linux) hoặc `run.bat` (Windows).

## Điều khiển & Khả năng tiếp cận

| Phím | Tác dụng |
|---|---|
| `W A S D` / Phím mũi tên | Bơi ngang & lặn/nổi (`gather`) · Đi lại trên nhà bè (`quan`) |
| `E` (`interact`) | Cập bến / hái rau mặt nước (`gather`) · Nấu / bưng / phục vụ (`quan`) |
| `Space` (`catch`) | Bắt đàn cá khi đang lặn dưới nước |
| `Esc` / `P` (`pause`) | Tạm dừng / Tiếp tục (dừng đồng hồ, timer, hao tươi và cả Shop) |
| `H` | Bật/tắt **Chế độ tương phản cao** (có sẵn nút trên Menu, Pause & góc phải HUD) |
| `R` | Chơi lại từ đầu |

- **3 cảnh báo trực quan bằng chữ + biểu tượng** (hoạt động rõ cả ở chế độ thường và tương phản cao): `⚠ 🐊 THỦY QUÁI GẦN!`, `⚠ 🫧 OXY SẮP HẾT!` / `☠ 🫧 HẾT HƠI!`, và `⚠ 😠 KHÁCH BÀN T* SẮP GIẬN!`.

## Lệnh Test, Headless, Benchmark, Soak & Đóng gói

```bash
# 1. Bộ kiểm thử tự động (82 ca: Contract v1.0–v1.3, độ tươi, bench, soak, live)
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v

# 2. Headless trọn 1 Ngày (hoặc 2 tiến trình độc lập nối kho cá thể v1.2)
python3 -m chonoi.headless --mode day --days 1 --seed 1 --ticks 22200 --out day1.jsonl
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --inventory-out kho.json --out gather.jsonl
python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --inventory kho.json --out quan.jsonl

# 3. Benchmark có render 1280×720 (3s làm nóng + 30s đo)
python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

# 4. Soak headless 10 Ngày (bot tất định, lặp kế hoạch D1–D5 ở Ngày 6–10)
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

# 5. Đóng gói bản phát hành v1.0.0
python3 tools/package_release.py
```

> Trên Windows PowerShell: thay `PYTHONPATH=tests:. python3` bằng `$env:PYTHONPATH="tests;."; python`.

## Cách tính điểm, độ tươi & nâng cấp
- **Độ tươi (`tuning.freshness`):** Hàng mới `100`, hao `-0.5/s` trong giỏ và `-0.25/s` trong kho quán (Shop và món chín không hao; `Pause` dừng hao). Hàng `< 30` bị ươn (`spoiled`), không dùng nấu.
- **Giá & boa:** Khi nấu, `base_price = floor(giá niêm yết × trung bình fresh / 100)`. Phục vụ khi kiên nhẫn `≥ 50%` thưởng boa `floor(base_price × 0.2)` và uy tín `+0.2` (kẹp `[0, 5]`); khách hết kiên nhẫn bỏ đi `-0.5` uy tín.
- **Điểm tổng:** `score = earned + 100 × floor(reputation)`. Nâng cấp Shop (`oxygen`, `hp`) trừ `money`, giữ nguyên `earned`/`score` và có hiệu lực từ Ngày kế tiếp.

## Mở rộng & Sáng tạo của nhóm
- Nhóm SKT1 có 2 thành viên nên tập trung hoàn thiện **100% lõi Test Contract v1.3** (không bật extension), đạt tất định từng byte và hiệu năng vượt chuẩn.

## Tài liệu, Kiểm chứng & Giấy phép
- Thành viên & thỏa thuận: [`TEAM.md`](TEAM.md) · Giấy phép: [`LICENSE`](LICENSE) · Nguồn tài sản: [`CREDITS.md`](CREDITS.md)
- Release Notes & Lịch sử thay đổi: [`docs/release-notes-v1.0.0.md`](docs/release-notes-v1.0.0.md), [`CHANGELOG.md`](CHANGELOG.md)
- Hợp đồng & ADR: [`docs/contracts/README.md`](docs/contracts/README.md), [`docs/adr/0001-freshness-individual-inventory.md`](docs/adr/0001-freshness-individual-inventory.md)
- Ma trận truy vết & Bằng chứng: `docs/verification/phase-{1..4}.md` · `docs/proof/phase-{1..4}/`
- Retro, Clarify, AI Log & Phản tư: [`docs/retro.md`](docs/retro.md), [`docs/clarify.md`](docs/clarify.md), [`docs/standup.md`](docs/standup.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`docs/members/trungtk03.md`](docs/members/trungtk03.md), [`docs/members/DungNguyen74.md`](docs/members/DungNguyen74.md)
