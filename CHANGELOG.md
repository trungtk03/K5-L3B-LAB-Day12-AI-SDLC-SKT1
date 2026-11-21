# Changelog

## Phase 2 (`phase-2`) — 2026-11-21
- **Test Contract v1.1 (`game.contract.json`, `chonoi/{contract,inventory,inputs,scenario,headless}.py`):** Nâng cấp manifest lên `1.1`, đủ 6 nguyên liệu (`ca_keo`, `keo_neo`), 6 món ăn, 6 nút hái `N1–N6`, 2 bếp `B1–B2`, 4 bàn `T1–T4`, thông số cá bơi/sinh, Cá Sấu `M1–M2`, `day_plan` D1–D5, `shop.upgrades`, CLI `--mode day --days 1..5`, nút `pause`/`shop_done`/`buy`.
- **Gather v1.1 (`chonoi/sim/gather.py`):** 8 đàn cá đầu ca tại 8 điểm khác nhau, cá bơi `1.5 m/s` phản xạ mép/góc + đổi hướng mỗi 120 tick + sinh cá tại `360·k` (trần 12); Cá Sấu Năm Chèo `M1` (Ngày 1) & `M2` (Ngày 3) với `patrol`/`chase`/`recoil`, chạm mất 1 Máu + rơi `floor(n/2)` LIFO + `invuln_ticks=90`, ngất `cause="monster"`.
- **Quán, Vòng Ngày, Shop & Pause (`chonoi/sim/{quan,shop,day}.py`, `chonoi/runner.py`):** Lọc thực đơn theo `day_plan`, đổi pha cùng tick `gather → quan → shop`, Shop mua `oxygen`/`hp` (trừ `money`, giữ `earned`, áp từ Ngày kế), `pause` dừng mọi timer ở cả 3 mode.
- **Menu, Pause & HUD (`chonoi/live.py`, `chonoi/web/index.html`):** Menu chính (`Chơi`/`Thoát`), màn `DayIntro`/`EveningIntro`/`DayResult`/`Shop`/`Summary`, menu `Pause` (`Esc`/`P`), HUD chữ không chân `≥ 18px` với cảnh báo oxy `< 25%`, giờ `≤ 30s`, kiên nhẫn `< 25%`, “Thủy quái!” + viền tím, “Hết hơi!” và kho khả dụng.
- **Kiểm thử & Bằng chứng:** 70/70 test tự động xanh (`test_gather_p2.py`, `test_day_p2.py`, regression P1, `test_live.py`), 1 Ngày 22.200 tick chạy ~1.0s (≤ 20s), SHA-256 tất định 100%, proof tại `docs/proof/phase-2/`, `docs/verification/phase-2.md` và retro nhanh tại `docs/retro.md`.

## Phase 1 (`phase-1`) — 2026-11-21
- **Lát 1 & Lát 2 (`chonoi/sim/gather.py`):** Hoàn thiện bơi, lặn/nổi (`dive`/`surface`), oxy, ngạt (`oxygen_empty`/`choke`), 3 Máu, ngất (`faint` mất giỏ LIFO), hái rau mặt nước (`gather`/`node_regrown`), bắt cá dưới nước (`fish_caught`), sức chứa giỏ (`hold_full`), cập bến và ghi file kho nguyên tử.
- **Lát 3 & Lát 4 (`chonoi/sim/quan.py`):** Hoàn thiện lịch khách (`customer_arrived`/`no_dish`), giữ chỗ nguyên liệu (`reserved`), kiên nhẫn & rời quán (`customer_left`), ưu tiên tương tác (khoảng cách → Bếp trước Bàn → id), nấu (`cook_started`/`dish_ready`), bưng (`dish_picked`), phục vụ (`served`), tính boa, thanh toán (`paid`), uy tín và kết thúc ca (`quan_end`).
- **Kiểm scenario (`chonoi/scenario.py`):** Bổ sung kiểm mâu thuẫn mức luật cho `quan` thoát mã 2 trước khi ghi đầu ra.
- **Kiểm thử & Bằng chứng:** 54/54 test tự động xanh, ma trận truy vết `docs/verification/phase-1.md` và bằng chứng thực tế trong `docs/proof/phase-1/`.
