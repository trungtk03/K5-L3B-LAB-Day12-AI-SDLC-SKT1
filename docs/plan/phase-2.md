# Kế hoạch Phase 2 — Nhóm SKT1 (55 phút · Contract v1.1)

## Mục tiêu
Hoàn thiện toàn bộ lõi TICKET-02 & Test Contract v1.1 trước mốc `1:55`:
1. Chốt manifest `contract_version: "1.1"` với số liệu chuẩn (6 nguyên liệu, 6 món, 6 nút hái, 2 bếp, 4 bàn, cá bơi/sinh, Cá Sấu M1–M2, `day_plan` D1–D5, `shop.upgrades`).
2. Buổi sáng (`gather`): đàn cá bơi + phản xạ mép + sinh theo lịch; Cá Sấu Năm Chèo (`patrol`/`chase`/`recoil`/hit/invuln/ngất).
3. Buổi tối (`quan`): 2 bếp, 4 bàn, 6 món, lọc thực đơn theo `day_plan` khi chạy `day`.
4. Vòng ngày (`--mode day --days 1..5`), Shop nâng cấp `oxygen`/`hp`, Pause cả 3 mode, Menu & HUD hoàn chỉnh trên trình duyệt (`chonoi/web/index.html`).
5. Smoke tích hợp 2 tiến trình, smoke `day`, regression P1 xanh, bằng chứng `docs/proof/phase-2/`, `docs/verification/phase-2.md`, retro và tag `phase-2`.

## Phân công lát & phụ thuộc (2 thành viên SKT1)

| Lát | Công việc chính | Người phụ trách | File chính | Phụ thuộc |
|---|---|---|---|---|
| Nền v1.1 | Manifest v1.1, CLI `--mode day`/`--days`, `inputs` (`pause`/`shop_done`/`buy`), `inventory` 6 loại, `scenario` v1.1 | Nguyễn Hoàng Trung (`trungtk03`) | `game.contract.json`, `chonoi/{contract,inventory,inputs,scenario,headless}.py` | Tag `phase-1` |
| Lát 1 (P2) | 6 nút hái (`keo_neo`), 3 loài cá (`ca_keo`), 8 đàn đầu ca, cá bơi + phản xạ mép + sinh theo lịch | Nguyễn Tuấn Dũng (`DungNguyen74`) | `chonoi/sim/gather.py` | Nền v1.1 |
| Lát 2 (P2) | Cá Sấu Năm Chèo (`M1`/`M2`), `patrol`/`chase`/`recoil`, chạm rơi hàng LIFO, `invuln_ticks`, ngất do quái | Nguyễn Tuấn Dũng (`DungNguyen74`) | `chonoi/sim/gather.py`, `tests/test_gather_p2.py` | Lát 1 (P2) |
| Lát 3 (P2) | Quán 2 bếp `B1–B2`, 4 bàn `T1–T4`, 6 món, lọc `day_plan`, kế thừa tiền/uy tín qua Ngày | Nguyễn Hoàng Trung (`trungtk03`) | `chonoi/sim/quan.py` | Nền v1.1 |
| Lát 4 (P2) | `--mode day`, `ShopSim`, `Pause` cả 3 mode, đổi pha cùng tick, Menu/Chuyển pha/Shop/Pause/HUD | Nguyễn Hoàng Trung (`trungtk03`) | `chonoi/sim/{day,shop}.py`, `chonoi/{runner,live}.py`, `chonoi/web/index.html`, `tests/test_day_p2.py` | Lát 1–3 (P2) |
| QA & Release | Smoke tích hợp phút 20, regression P1 + P2, hiệu năng ≤ 20s, proof, verification, retro, tag `phase-2` | Cả hai (Integrator chốt tag) | `docs/proof/phase-2/`, `docs/verification/phase-2.md`, `docs/retro.md` | Lát 1–4 (P2) |

## Mốc kiểm tra
- **Phút 0–5:** Chốt nền Contract v1.1.
- **Phút 20:** Smoke tích hợp 2 tiến trình `gather --inventory-out` → `quan --inventory` lưu `docs/proof/phase-2/integration.*` + standup.
- **Phút 35–45:** Smoke `--mode day --days 1`, chạy nhiều Ngày kiểm nâng cấp, regression P1 xanh, hoàn thiện proof & ma trận truy vết.
- **Phút 45–55:** Retro nhanh trong `docs/retro.md`, gắn tag `phase-2`.
