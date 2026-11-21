# Kế hoạch Phase 4 — Phát hành v1.0.0 (30 phút · Contract v1.3)

## Phân công vai trò (Nhóm SKT1 — 2 thành viên)

| Vai trò | Việc chính | Người nhận | Sản phẩm đầu ra |
|---|---|---|---|
| **Bench / QA** | Triển khai `chonoi/bench.py` (`1280×720`, 3s warmup + 30s đo) và `chonoi/soak.py` (bot tất định 10 Ngày, lặp kế hoạch D1–D5); chạy full regression P1–P4; xuất bằng chứng | Nguyễn Tuấn Dũng (`DungNguyen74`) & Nguyễn Hoàng Trung (`trungtk03`) | `chonoi/bench.py`, `chonoi/soak.py`, `tests/test_release_p4.py`, `docs/proof/phase-4/*`, `docs/verification/phase-4.md` |
| **UI / Accessibility** | Hoàn thiện 3 cảnh báo chữ + biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) và Chế độ tương phản cao (phím `H` / nút bật tắt) | Nguyễn Hoàng Trung (`trungtk03`) | `chonoi/web/index.html` |
| **Đóng gói & Release / Integrator** | Nâng `game.contract.json` lên v1.3, viết `tools/package_release.py`, `LICENSE`, `CREDITS.md`, `README.md`, `CHANGELOG.md`, `docs/release-notes-v1.0.0.md`, thử giải nén sạch, gắn tag `phase-4` & `v1.0.0` | Nguyễn Hoàng Trung (`trungtk03`) | `game.contract.json`, `tools/package_release.py`, `dist/quan-an-cho-noi-v1.0.0.zip`, `docs/release-notes-v1.0.0.md` |
| **Điều phối Retro** | Rà hành động Phase 2, tổng hợp số liệu commit/review/AI log, hoàn thiện `docs/retro.md` & `docs/members/*.md` | Cả hai (`DungNguyen74`, `trungtk03`) | `docs/retro.md`, `docs/members/trungtk03.md`, `docs/members/DungNguyen74.md` |

## Mốc thời gian (30 phút)
- **0–15':** Contract v1.3, `bench.py`, `soak.py`, cảnh báo + tương phản cao, `package_release.py`, `LICENSE`/`CREDITS.md` và bộ test P4.
- **15–25':** Chạy bench thật 30s, soak thật 10 Ngày (2 lần kiểm tất định), kiểm bản đóng gói sạch, regression toàn bộ, hoàn thiện `docs/verification/phase-4.md`, `docs/retro.md` và phản tư cá nhân.
- **25–30':** Chốt `CHANGELOG.md`, `docs/release-notes-v1.0.0.md`, kiểm working tree sạch, gắn tag `phase-4` & `v1.0.0` trước mốc `3:00`.
