# Hợp đồng tích hợp Phase 1 — Nhóm SKT1 (Contract v1.0)

> Chốt bởi Integrator (`trungtk03`) và PO/QA (`DungNguyen74`). Mọi thay đổi hợp đồng phải báo cả nhóm và cập nhật tài liệu này.

## 1. Schema file kho (`inventory.json`, Contract G)

File kho truyền dữ liệu giữa hai tiến trình `gather` (`--inventory-out`) và `quan` (`--inventory`):

- Định dạng JSON UTF-8, duy nhất một khóa gốc `"items"`:
  ```json
  {"items":{"bong_sung":2,"ca_loc":1}}
  ```
- Khóa trong `"items"` chỉ thuộc 4 nguyên liệu Phase 1: `bong_dien_dien`, `bong_sung`, `ca_linh`, `ca_loc`, sắp theo thứ tự chữ cái, bỏ mục bằng `0`, giá trị là số nguyên dương.
- Ghi nguyên tử qua file tạm cùng thư mục, chỉ ghi **đúng một lần** khi `gather` kết thúc (`gather_end`). Nếu dừng do `tick_limit` thì không tạo/sửa file đích.
- Đọc sai schema / id lạ / số âm / trùng với `scenario.quan.stock` → thoát mã `2` trước khi ghi đầu ra.
- Ví dụ hợp lệ: [`inventory.sample.json`](inventory.sample.json).

## 2. Giao diện giữa `sim/*` và `client/ui` (`chonoi/live.py` & `chonoi/web/index.html`)

- **Lệnh từ UI vào sim (`POST /input`):**
  - `{"move": [dx, dy], "interact": bool, "catch": bool}` (trong đó `move` chuẩn hóa biên độ `<= 1`; `interact` và `catch` kích hoạt theo cạnh lên `false -> true`).
  - `POST /restart`: khởi tạo lại `Session` với cùng `seed` và `scenario`.
- **Trạng thái UI đọc từ sim (`GET /state`):**
  - Trường chung: `tick`, `sim_tick`, `mode`, `phase`, `phase_tick`, `state`, `time_left_ticks`, `money`, `earned`, `reputation`, `score`, `meta`, `events`, `finished`, `reason`, `error`.
  - Riêng `gather`: `player` (`pos`, `vel`, `heading_deg`, `oxygen_ticks`, `oxygen_max_ticks`, `hp`, `hp_max`, `zero_oxy_ticks`, `invuln_ticks`, `catch_cd_ticks`, `at_surface`), `hold`, `hold_count`, `hold_capacity`, `nodes`, `fish`.
  - Riêng `quan`: `player` (`pos`), `stock`, `hand` (`null` hoặc `{order_id, dish_id, base_price}`), `stoves` (`id`, `pos`, `state`, `dish`, `order_id`, `cook_ticks_left`, `ready_ticks`), `tables` (`id`, `pos`, `customer_id`), `customers`.

## 3. Danh sách sự kiện (JSONL `type: "event"`)

### Buổi sáng (`gather`, phát bởi `chonoi/sim/gather.py`)
| Tên sự kiện | `data` | Khi nào phát |
|---|---|---|
| `dive` | `{"pos": [x, d]}` | Chuyển từ mặt nước (`d <= surface_depth`) xuống dưới nước |
| `surface` | `{"pos": [x, d]}` | Chuyển từ dưới nước lên mặt nước |
| `oxygen_empty` | `{"oxygen_ticks": 0}` | Oxy giảm từ `> 0` về `0` khi ở dưới nước |
| `choke` | `{"hp": int}` | Đủ `choke_interval_ticks` (60) với `oxygen_ticks == 0` dưới nước, trừ 1 Máu |
| `faint` | `{"cause": "choke", "lost": [...], "hp": 0}` | Máu về 0; `lost` theo thứ tự LIFO |
| `gather` | `{"node_id", "kind", "amount"}` | Hái thành công nút ở mặt nước |
| `node_regrown` | `{"node_id"}` | `regrow_ticks` giảm về `0` |
| `fish_caught` | `{"fish_id", "kind", "yield"}` | Bắt thành công đàn cá dưới nước |
| `hold_full` | `{"action": "gather"\|"catch", "node_id"\|"fish_id", "required", "free"}` | Giỏ không đủ chỗ trống |
| `gather_end` | `{"reason": "docked"\|"time"\|"fainted", "inventory": {"items": {...}}}` | Kết thúc buổi sáng |

### Buổi tối (`quan`, phát bởi `chonoi/sim/quan.py`)
| Tên sự kiện | `data` | Khi nào phát |
|---|---|---|
| `customer_arrived` | `{"order_id", "table_id", "dish_id"}` | Khách mới vào bàn trống theo lịch, giữ chỗ nguyên liệu |
| `no_dish` | `{}` | Tới lịch khách mới, có bàn trống nhưng kho khả dụng không đủ nấu món nào |
| `cook_started` | `{"stove_id", "order_id", "dish_id", "items": {...}, "base_price"}` | Tương tác bếp rảnh, trừ kho theo công thức và bắt đầu nấu đơn giữ chỗ cũ nhất |
| `dish_ready` | `{"stove_id", "order_id", "dish_id"}` | `cook_ticks_left` giảm về `0`, bếp chuyển `ready` (`ready_ticks = 0`) |
| `dish_picked` | `{"stove_id", "order_id", "dish_id"}` | Nhấc món từ bếp `ready` lên tay rỗng, bếp về `idle` |
| `served` | `{"order_id", "table_id", "dish_id", "patience_ticks_left", "base_price", "tip"}` | Phục vụ món khớp `order_id` tại bàn, khách chuyển `eating` |
| `paid` | `{"order_id", "table_id", "base_price", "tip", "amount", "reason": "finished_eating"\|"closing"}` | Khách ăn xong hoặc hết giờ ca, thanh toán tiền và cộng uy tín nếu `tip > 0` |
| `customer_left` | `{"order_id", "table_id", "reason": "patience"\|"closing", "reputation"}` | Khách chờ hết kiên nhẫn (trừ uy tín) hoặc hết giờ ca (không trừ uy tín) |
| `quan_end` | `{"reason": "time", "money", "earned", "shift_earned", "reputation"}` | Hết giờ ca buổi tối |
