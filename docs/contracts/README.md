# Hợp đồng tích hợp Phase 2 — Nhóm SKT1 (Contract v1.1)

> Chốt bởi Integrator (`trungtk03`) và PO/QA (`DungNguyen74`). Nâng cấp từ v1.0 lên v1.1 theo TICKET-02.

## 1. Schema file kho (`inventory.json`, Contract G)

- Định dạng JSON UTF-8, duy nhất khóa gốc `"items"`:
  ```json
  {"items":{"bong_sung":2,"ca_loc":1}}
  ```
- Khóa hợp lệ (6 nguyên liệu v1.1): `bong_dien_dien`, `bong_sung`, `keo_neo`, `ca_linh`, `ca_loc`, `ca_keo`, sắp theo khóa, bỏ mục 0, giá trị nguyên dương.
- Ghi nguyên tử đúng 1 lần khi `gather_end` (ở `--mode gather --inventory-out`). Trong `--mode day`, kho được bàn giao tự động trong bộ nhớ giữa `gather` → `quan` (kể cả khi `fainted` → kho rỗng).
- Ví dụ hợp lệ: [`inventory.sample.json`](inventory.sample.json).

## 2. Chế độ CLI & Inputs v1.1

- Modes: `--mode gather | quan | day`. Cờ `--days N` (`1..5`, mặc định `1`) chỉ dùng với `--mode day`.
- Nút boolean (cạnh lên `false -> true`, giữ qua đổi pha không tạo cạnh mới): `interact`, `catch`, `pause`, `shop_done`.
- Trường một bước `buy` (chuỗi khác rỗng, không kế thừa): `"oxygen"`, `"hp"` trong pha `shop`.
- `pause` áp dụng cho cả 3 mode: vào pause chỉ tăng `tick` ngoài, đóng băng `sim_tick`, `phase_tick` và mọi timer (kể cả Shop), phát `paused` và `state: "paused"`; cạnh `pause` tiếp theo phát `resumed` và chạy gameplay ngay trong bước đó.

## 3. Giao diện giữa `sim/*` và `client/ui` (`chonoi/live.py` & `chonoi/web/index.html`)

- `POST /input`: `{"move": [dx, dy], "interact": bool, "catch": bool, "pause": bool, "shop_done": bool, "buy": str}`
- `POST /restart`: khởi tạo lại `Session` từ đầu.
- `GET /state`: snapshot JSON hiện tại + `meta` (toàn bộ `tuning`), `events`, `finished`, `reason`, `error`, `stats` (thống kê ca & tổng kết).
- Snapshot `gather` bổ sung `monsters[]` (`id`, `kind`, `pos`, `state`, `state_ticks_left`, `target_idx`, `waypoints`, `recoil_dir`) và `fish[].age_ticks`.
- Snapshot `day` bổ sung `day`, `day_plan`, `upgrades`, `active_upgrades`, `phase` (`gather`/`quan`/`shop`), và trong pha `shop` có `stock` dư + `time_left_ticks`.

## 4. Danh sách sự kiện v1.1

### Chung & Pause
| Tên sự kiện | `data` | Ghi chú |
|---|---|---|
| `paused` / `resumed` | `{}` | Chuyển trạng thái tạm dừng / tiếp tục |

### Buổi sáng (`gather`)
| Tên sự kiện | `data` | Ghi chú |
|---|---|---|
| `dive` / `surface` | `{"pos": [x, d]}` | Lặn xuống / nổi lên qua `surface_depth` |
| `oxygen_empty` | `{"oxygen_ticks": 0}` | Oxy vừa chạm 0 dưới nước |
| `choke` | `{"hp": int}` | Ngạt mỗi 60 tick (tính cả bước chạm 0), xuyên bất tử |
| `monster_hit` | `{"monster_id", "hp", "lost": [...], "pos": [x, d]}` | Cá Sấu chạm (`≤ 1.5 m`, `d ≥ 10`, hết bất tử), mất `floor(n/2)` LIFO |
| `faint` | `{"cause": "choke"\|"monster", "lost": [...], "hp": 0}` | Máu chạm 0, mất phần giỏ còn lại theo LIFO |
| `gather` / `node_regrown` | `{"node_id", "kind", "amount"}` / `{"node_id"}` | Hái nút mặt nước & mọc lại sau 20s |
| `fish_caught` / `fish_spawned` | `{"fish_id", "kind", "yield"}` / `{"id", "kind", "pos"}` | Bắt đàn cá (vị trí trước khi bơi) & sinh đàn mới tại `360·k` |
| `hold_full` | `{"action", "node_id"\|"fish_id", "required", "free"}` | Giỏ không đủ chỗ |
| `gather_end` | `{"reason": "docked"\|"time"\|"fainted", "inventory": {"items": {...}}}` | Kết thúc buổi sáng |

### Buổi tối (`quan`)
`customer_arrived`, `no_dish`, `cook_started`, `dish_ready`, `dish_picked`, `served`, `paid` (`finished_eating`/`closing`), `customer_left` (`patience`/`closing`), `quan_end`.

### Vòng ngày (`day`) & Shop (`shop`)
| Tên sự kiện | `data` | Ghi chú |
|---|---|---|
| `day_start` / `phase_start` | `{}` | Mở Ngày mới / mở pha mới (`phase_tick: 0`) |
| `day_plan` | `{"dishes": {...}, "ingredients": {...}}` | Kế hoạch món & tổng nguyên liệu Ngày |
| `bought` | `{"upgrade", "level", "price", "money"}` | Mua nâng cấp thành công (trừ `money`, giữ `earned`) |
| `buy_failed` | `{"action", "reason": "funds"\|"max_level"\|"unknown"}` | Mua thất bại |
| `shop_end` | `{"reason": "done"\|"time"}` | Đóng Shop, tăng `days_completed` |
