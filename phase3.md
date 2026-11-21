# TICKET-03 — Change Request “Mùa Nước Nổi” (Phase 3)

> 35 phút (1:55–2:30) · Test Contract v1.2 · Hạn đẩy tag `phase-3` 2:30.

Tháng Tám âm lịch, nước lũ về, cá linh nhiều. Trời nóng làm nguyên liệu mau ươn. Khách hàng muốn biết độ tươi của từng nguyên liệu, từ lúc Út Sen lấy được đến khi đưa vào bếp.

## 1. Lõi (mọi nhóm) — Độ tươi & Kho cá thể (Contract v1.2)
- **[THAY THẾ] Kho đếm → Kho cá thể:**
  `{"items":[{"id":"I1","kind":"ca_linh","fresh":100},{"id":"I2","kind":"ca_loc","fresh":97.5}]}`
  - Kho rỗng: `{"items":[]}`. `id` duy nhất khác rỗng, `kind` thuộc 6 nguyên liệu, `fresh` hữu hạn trong `[0, 100]`.
  - Cấp `I1, I2, …` theo thứ tự vào giỏ, tăng xuyên pha và Ngày (kể cả khi cá thể trước đã dùng hoặc bỏ). LIFO khi mất hàng vẫn theo thứ tự vào giỏ.
  - Contract v1.2 trả mã `2` cho file kho đếm hoặc sai schema / kind lạ / id trùng / fresh ngoài miền.
  - Xuất file `inventory.json` theo thứ tự `id`, đủ độ chính xác khi đọc lại ở ngưỡng 30.
- **Hao tươi & Ươn:**
  - Hàng mới `fresh = 100` lúc bắt/hái, bắt đầu hao từ bước sau.
  - Giỏ (`gather`): `-0.5/s` (`-1/120` mỗi tick). Kho quán (`quan`): `-0.25/s` (`-1/240` mỗi tick, kể cả hàng đang giữ chỗ). Kẹp đáy `0`. `Pause` dừng hao tươi. Món chín và hàng thô ở Shop không hao.
  - Ươn khi `fresh < 30` (so trước khi làm tròn): vẫn chiếm ô, không dùng nấu. Phát `spoiled` (`{item_id, kind, location}`) đúng 1 lần khi đi từ `≥ 30` xuống `< 30` (nhiều cá thể cùng vượt ngưỡng phát theo `id`).
- **[THAY THẾ] Giữ theo lượng → Giữ theo `id`:**
  - Mỗi loại trong công thức lấy các cá thể khả dụng tươi nhất, hòa theo `id`.
  - Nếu phần giữ có cá thể vừa ươn: nhả toàn bộ phần giữ của đơn và thử giữ lại đúng 1 lần theo thứ tự `order_tick` rồi `table_id`. Không đủ → `order_status = "unfulfillable"`, khách chờ tới hạn.
- **[THAY THẾ] Giá niêm yết → Giá theo tươi:**
  - Khi bắt đầu nấu (`cook_started`), tiêu đúng các `id` đang giữ và chốt `base_price = floor(giá niêm yết × trung bình fresh / 100)`.
  - Boa `floor(base_price × 0.2)` tính trên giá đã chốt. `cook_started.data.items` là mảng cá thể sắp theo `kind` rồi `id`. `lost` trong `monster_hit`/`faint` là mảng cá thể theo thứ tự bỏ LIFO.
- **Thứ tự trong tick:**
  - **Gather:** Đồng hồ, cooldown, hồi nút và hao tươi hàng sẵn có đầu bước → bơi, oxy, ngạt → thủy quái/hit → bến trước hái → bắt cá → hết giờ → nếu còn giờ: cá bơi & sinh cá.
  - **Quán:** Đồng hồ & timer → hao tươi kho thô, phát hết `spoiled` theo `id` rồi mới xử lý giữ chỗ bị ươn → xét món chín theo `id` bếp → di chuyển & tối đa 1 tương tác → thanh toán, kiên nhẫn/đóng ca → nếu còn giờ: khách mới. Giao đúng tick kiên nhẫn = 0 vẫn hợp lệ; giao đúng tick hết ca được trả ngay.
- **Manifest v1.2:** `contract_version: "1.2"`, thêm `tuning.freshness = {initial: 100, gather_decay_per_s: 0.5, quan_decay_per_s: 0.25, spoiled_below: 30}`.
- **HUD:** Cho người chơi đọc được độ tươi và nhận biết rõ hàng ươn.
