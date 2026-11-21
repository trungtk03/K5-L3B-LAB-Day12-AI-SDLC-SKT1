# Hợp đồng tích hợp Phase 3 — Nhóm SKT1 (Contract v1.2)

> Chốt bởi Integrator (`trungtk03`) và PO/QA (`DungNguyen74`). Nâng cấp từ v1.1 lên v1.2 theo TICKET-03 ("Mùa Nước Nổi"). Chi tiết quyết định thiết kế tại [ADR-0001](../adr/0001-freshness-individual-inventory.md).

## 1. [BREAKING CHANGE] Schema file kho cá thể (`inventory.json`, Contract G v1.2)

- Định dạng JSON UTF-8, duy nhất khóa gốc `"items"` là **mảng cá thể** sắp theo `id_key`:
  ```json
  {"items":[{"id":"I1","kind":"ca_loc","fresh":100},{"id":"I2","kind":"bong_sung","fresh":97.5}]}
  ```
- Kho rỗng: `{"items":[]}`.
- Mỗi phần tử có đúng 3 khóa `{id, kind, fresh}`: `id` chuỗi duy nhất khác rỗng, `kind` thuộc 6 nguyên liệu (`bong_dien_dien`, `bong_sung`, `keo_neo`, `ca_linh`, `ca_loc`, `ca_keo`), `fresh` số hữu hạn trong `[0, 100]`.
- **Từ chối kho đếm cũ:** Contract v1.2 trả mã thoát `2` trước khi ghi đầu ra nếu `items` là object đếm (`{"ca_loc": 1}`), sai schema, `id` trùng, `kind` lạ hoặc `fresh` ngoài `[0, 100]`.
- Cấp phát `I1, I2, ...` theo thứ tự vào giỏ, tăng liên tục xuyên pha và xuyên Ngày (kể cả sau khi cá thể trước đã tiêu dùng/rơi mất).
- Ghi nguyên tử qua file tạm cùng thư mục, đủ độ chính xác float khi đọc lại để bảo toàn ngưỡng `30` (khôi phục nội bộ bằng `Fraction.limit_denominator(10**9)`).
- Ví dụ hợp lệ: [`inventory.sample.json`](inventory.sample.json).

## 2. Độ tươi, ươn, giữ chỗ theo `id` & tính giá (`tuning.freshness`)

| Tham số | Giá trị chuẩn | Quy tắc |
|---|---|---|
| `initial` | `100` | Hàng vừa hái/bắt có `fresh = 100`, bắt đầu hao từ bước sau |
| `gather_decay_per_s` | `0.5` (`-1/120`/tick) | Hao đầu bước cho hàng sẵn có trong giỏ; `Pause` dừng hao |
| `quan_decay_per_s` | `0.25` (`-1/240`/tick) | Hao đầu bước cho toàn bộ kho quán (kể cả hàng đang giữ); Shop & món chín không hao |
| `spoiled_below` | `30` | So trước khi làm tròn; đi từ `≥ 30` xuống `< 30` phát `spoiled` đúng 1 lần theo `id` |

- **Giữ chỗ theo `id`:** `customers[].reserved` là mảng `id` cá thể tươi nhất chưa bị giữ (hòa theo `id`). Khi cá thể đang giữ vừa ươn, nhả toàn bộ phần giữ của đơn và thử giữ lại đúng 1 lần theo `(order_tick, table_id)`; thất bại chuyển `order_status: "unfulfillable"`.
- **Giá theo độ tươi:** khi `cook_started`, tiêu đúng các `id` đang giữ và chốt `base_price = floor(giá niêm yết × trung bình fresh / 100)`. Tiền boa `floor(base_price × 0.2)` áp trên `base_price` đã chốt.

## 3. Sự kiện & JSONL thay đổi ở v1.2

| Sự kiện / Trường | Định dạng v1.2 |
|---|---|
| `spoiled` (mới) | `{"item_id": "I1", "kind": "ca_linh", "location": "hold"\|"stock"}` |
| `cook_started.data.items` | Mảng cá thể `[{id, kind, fresh}, ...]` sắp theo `(kind, id)` |
| `monster_hit.data.lost` / `faint.data.lost` | Mảng cá thể `[{id, kind, fresh}, ...]` theo thứ tự bỏ LIFO |
| `gather_end.data.inventory` | `{"items": [{id, kind, fresh}, ...]}` sắp theo `id` |
| Snapshot `hold`, `stock` (quán & Shop) | Mảng cá thể `[{id, kind, fresh}, ...]` (`hold` theo thứ tự LIFO, `stock` theo `id`) |
| Snapshot `customers[].reserved` | Mảng `id` cá thể `["I1", ...]` |
