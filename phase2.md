# TICKET-02 — Một ngày ở chợ nổi (Phase 2)

> 55 phút (1:00–1:55) · Test Contract v1.1 · Hạn đẩy tag `phase-2` 1:55.

Hai buổi đã nối được. Khách hàng chốt số liệu chuẩn và muốn chơi trọn một vòng ngày. Sáng, Út Sen xem thực đơn để biết cần tìm nguyên liệu gì. Tối, quán dùng phần mang về để phục vụ. Cuối ngày, người chơi dùng tiền mua nâng cấp cho lần lặn sau.

## 1. Lõi (mọi nhóm) — Số liệu chuẩn
Tiền tính theo nghìn đồng, mô phỏng chạy 60 tick/s.

### 1.1. Buổi sáng — Lặn & Hái
- **Thời lượng:** 180 s (10.800 tick).
- **Vùng nước:** `x ∈ [0,100]`, `d ∈ [0,30]`. Chặn ở các mép. Mặt nước ở `d ≤ 0.5`. Nông `d < 10`, giữa `10 ≤ d < 20`, sâu `d ≥ 20`.
- **Bến & xuất phát:** Bến tâm `[2,0]`, bán kính `3 m`. Xuất phát `[2,0]`, hướng `0°` (`+x`).
- **Bơi:** `4.0 m/s`, đạt tốc độ hoặc dừng trong `≤ 6` tick.
- **Oxy & ngạt:** Cơ sở `30 s` (`1.800` tick). Dưới nước `-1/tick`, mặt nước `+6/tick`, kẹp ở tối đa. Ở dưới nước với oxy = 0, mất 1 Máu mỗi `60` tick, tính cả bước vừa chạm 0. Reset nhịp khi oxy > 0 hoặc lên mặt nước. Ngạt xuyên bất tử và không làm rơi hàng.
- **Giỏ & hái:** `12` ô. Hái ở mặt nước trong `≤ 2.0 m`, lấy `1`, mọc lại sau `20 s` (`1.200` tick). Xét bến trước nút hái.
- **Nút hái:** `N1 [12,0]`, `N2 [28,0]` (`bong_dien_dien`); `N3 [44,0]`, `N4 [60,0]` (`bong_sung`); `N5 [76,0]`, `N6 [90,0]` (`keo_neo`).
- **Bắt cá:** `catch` (`Space`), dưới nước, chọn gần nhất trong `≤ 2.0 m`, hòa theo `id`. Đủ chỗ cho cả đàn. Hồi `0.5 s` (`30` tick) từ lần bắt thành công. Yield: `ca_linh` 3, `ca_loc` 1, `ca_keo` 2.
- **Đàn cá bơi:** `1.5 m/s` trong `x ∈ [4,96]`, độ sâu `ca_linh [3,12]`, `ca_loc [8,20]`, `ca_keo [22,28]`. Đổi hướng theo seed ở bước bơi thứ `120, 240…` trước khi di chuyển. Phản xạ phần quãng đường còn lại khi chạm mép, đảo thành phần hướng vuông góc (góc đảo cả hai).
- **Điểm sinh & sinh cá:** `x ∈ {15,30,45,60,75,90}`, `d`: `ca_linh {5,10}`, `ca_loc {10,16}`, `ca_keo {24,27}` (36 cặp loài–vị trí, 30 vị trí hình học). Đầu ca 8 đàn ở 8 điểm khác nhau, trần 12 đàn. Tại `phase_tick = 360·k (k ≥ 1)`, sau khi cá bơi, sinh tối đa 1 đàn nếu `< 12` và có điểm cách mọi đàn sống `> 1 m`. Trọng số `ca_linh 40%`, `ca_loc 30%`, `ca_keo 30%` chuẩn hóa trên các loài còn điểm hợp lệ → chọn đều 1 điểm → hướng theo seed. Cá mới tham gia từ bước sau.
- **Kết thúc:** `docked`, `time` (giữ giỏ), `fainted` (Máu = 0, mất toàn bộ giỏ).

### 1.2. Cá Sấu Năm Chèo, Máu và ngất
- Máu cơ sở `3`, hồi đầy đầu mỗi Ngày. Cá Sấu ở `d ∈ [10,30]`. `M1` từ Ngày 1 `[60,24] ↔ [64,24]`, `M2` từ Ngày 3 `[85,18] ↔ [89,18]`. Trong `gather` độc lập dùng bố trí Ngày 1.
- `patrol` `1.0 m/s` tới waypoint, tới nơi đổi waypoint cho bước sau. Người chơi ở `d ≥ 10` và cách `≤ 10 m` → `chase` `3.0 m/s`. Rời `chase` khi cách `> 16 m` hoặc người chơi lên `d < 10`.
- Chạm sau khi cả hai di chuyển: cách `≤ 1.5 m`, `d ≥ 10`, hết bất tử → mất 1 Máu, rơi `floor(len(hold)/2)` LIFO, bất tử `90` tick, tối đa 1 hit/bước (gần nhất, hòa theo `id`). Con gây hit vào `recoil` `60` bước tính từ bước sau, lùi `2/60 m` mỗi bước theo hướng xa người chơi (trùng tâm `+x`), không gây hit; hết `recoil` về `patrol`, xét phát hiện/chạm từ bước kế. Máu = 0 → ngất ngay và mở quán tối với kho rỗng.

### 1.3. Buổi tối — Mở Quán & Thực đơn (6 món)
- Phòng `x ∈ [0,16]`, `z ∈ [0,10]`, xuất phát `[8,5]`, đi `4.0 m/s`, ramp `≤ 6` tick.
- Bếp: `B1 [2,8]`, `B2 [5,8]`. Bàn: `T1 [9,2]`, `T2 [13,2]`, `T3 [9,6]`, `T4 [13,6]`.
- Khách: `120 + 900·k`, kiên nhẫn `60 s`, ăn `10 s`, boa `floor(price × 0.2)` nếu còn `≥ 50%` kiên nhẫn (+0.2 uy tín), hết kiên nhẫn `-0.5` uy tín, kẹp `[0,5]`. `burn_s: null`.
- Thực đơn: `ca_loc_nuong_trui` (`ca_loc ×1`, 6s, 60), `goi_bong_sung` (`bong_sung ×2`, 4s, 40), `lau_ca_linh_dien_dien` (`ca_linh ×3 + bong_dien_dien ×1`, 10s, 120), `canh_chua_ca_loc` (`ca_loc ×1 + bong_dien_dien ×1`, 8s, 90), `ca_keo_nuong` (`ca_keo ×2`, 6s, 70), `lau_mam` (`ca_linh ×2 + ca_keo ×1 + keo_neo ×1 + bong_dien_dien ×1`, 12s, 200).

## 2. Vòng ngày (`--mode day`), Kế hoạch D1–D5, Shop, Pause, Menu & HUD
- Vòng ngày: `DayIntro → gather → EveningIntro → quan → DayResult → Shop → DayIntro / Summary`.
- Kế hoạch D1–D5 theo bảng chuẩn; trong `day` khách chỉ gọi món trong kế hoạch của Ngày đó đủ nguyên liệu khả dụng.
- Shop: `oxygen` (Cấp 1: 200 → 45s; Cấp 2: 400 → 60s), `hp` (Cấp 1: 250 → 4 Máu; Cấp 2: 500 → 5 Máu). Trừ `money`, giữ `earned` & `score`; hiệu lực từ Ngày kế. Tự đóng sau `600` tick hoặc `shop_done`.
- Pause (`Esc`/`P` hoặc nút `pause`): dừng `sim_tick`, `phase_tick` và mọi timer ở cả 3 mode (kể cả Shop).

## 3. DoD Phase 2
- `contract_version: "1.1"`, số liệu chuẩn đủ 6 nguyên liệu, 6 món, 2 bếp/4 bàn, cá bơi/sinh, Cá Sấu M1/M2.
- Chơi trọn vòng ngày với Menu, Pause, HUD; `--mode day` đúng kế hoạch D1–D5, Shop & áp nâng cấp từ Ngày kế.
- Smoke tích hợp 2 tiến trình, `--mode day --days 1`, nhiều Ngày, regression P1 xanh, bằng chứng tại `docs/proof/phase-2/`, `docs/verification/phase-2.md`, retro, clarify, AI log, gắn tag `phase-2`.
