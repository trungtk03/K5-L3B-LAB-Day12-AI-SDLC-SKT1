# Changelog

## Phase 1 (`phase-1`) — 2026-11-21
- **Lát 1 & Lát 2 (`chonoi/sim/gather.py`):** Hoàn thiện bơi, lặn/nổi (`dive`/`surface`), oxy, ngạt (`oxygen_empty`/`choke`), 3 Máu, ngất (`faint` mất giỏ LIFO), hái rau mặt nước (`gather`/`node_regrown`), bắt cá dưới nước (`fish_caught`), sức chứa giỏ (`hold_full`), cập bến và ghi file kho nguyên tử.
- **Lát 3 & Lát 4 (`chonoi/sim/quan.py`):** Hoàn thiện lịch khách (`customer_arrived`/`no_dish`), giữ chỗ nguyên liệu (`reserved`), kiên nhẫn & rời quán (`customer_left`), ưu tiên tương tác (khoảng cách → Bếp trước Bàn → id), nấu (`cook_started`/`dish_ready`), bưng (`dish_picked`), phục vụ (`served`), tính boa, thanh toán (`paid`), uy tín và kết thúc ca (`quan_end`).
- **Kiểm scenario (`chonoi/scenario.py`):** Bổ sung kiểm mâu thuẫn mức luật cho `quan` (giữ chỗ vượt kho, đơn `assigned` phải có đúng 1 món, khách `eating` phải có `base_price` & `tip`), thoát mã 2 trước khi ghi đầu ra.
- **Kiểm thử & Bằng chứng:** 54 test tự động (gồm smoke hộp đen, Lát 1–4, E2E 2 tiến trình, live server), ma trận truy vết `docs/verification/phase-1.md` và bằng chứng thực tế trong `docs/proof/phase-1/`.
- **Tài liệu & AI Harness:** Cập nhật `TEAM.md`, `README.md`, `docs/contracts/README.md`, `AGENTS.md`, 2 team skills trong `.agents/skills/`, `docs/clarify.md`, `docs/standup.md`, `docs/ai-usage-log.md`, `docs/members/trungtk03.md`.
