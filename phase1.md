# PRD-0 — Quán Ăn Chợ Nổi (Phase 1)
Day 12 · AI SDLC · Nhóm 4–6 người · 60 phút (0:00–1:00) · Test Contract v1.0 · Hạn đẩy tag phase-1 1:00.

## 1. Chúng tôi muốn gì
Quán Ăn Chợ Nổi là game quản lý quán ăn mang bản sắc miền Tây Nam Bộ. Người chơi là Út Sen, cô bé ở chợ nổi Rạch Sen. Khi Má Tư đau lưng, Út Sen lặn bắt cá và hái rau trên sông Chín Khúc vào buổi sáng. Tối đến, em nấu và phục vụ khách trên nhà bè của Má Tư. Những gì mang về quyết định quán có thể bán món nào.

### Tự do sáng tạo
Ngoài yêu cầu của PRD và Test Contract, nhóm được tự do thêm nhân vật, loài cá hoặc cây, sinh vật mới, món ăn, khu vực, cơ chế nhỏ, sự kiện, câu chuyện, đồ họa, âm nhạc hoặc giao diện theo ý mình.
- Giữ đúng luật lõi, số chuẩn và Test Contract. Tắt phần tự thêm ở headless hoặc bảo đảm nó không đổi tick, sự kiện, tiền, uy tín và snapshot theo contract khi chạy test.
- Ghi ý tưởng đã làm vào mục “Sáng tạo của nhóm” trong README.md, kèm bằng chứng ngắn cho thấy lõi vẫn đúng.
- Làm lõi đúng trước, sáng tạo sau. Ưu tiên một ý tưởng gọn, chạy ổn và hoàn thiện. Điểm sáng tạo nằm ở hạng mục chất lượng sản phẩm, độ phức tạp không được cộng điểm.

## 2. Phạm vi Phase 1
### Lõi (mọi nhóm)
- **Buổi sáng (gather):** Bơi trong mặt cắt 2D của sông, theo chiều ngang và độ sâu `[x,d]`. Út Sen tiêu oxy dưới nước, hồi oxy khi nổi lên và có 3 Máu, chỉ mất do ngạt. Hái tại nút trên mặt nước và dùng nút bắt cá (`catch`) khi lặn. Bản mặc định có 6 đàn cá đứng yên. Giỏ có sức chứa giới hạn. Cập bến hoặc hết giờ thì bàn giao phần còn trong giỏ qua file kho. Ngất thì kết thúc buổi sáng với kho rỗng.
- **Buổi tối (quan):** Quán có 1 bếp B1, 1 bàn T1 và 3 món. Khách chọn món nấu được với kho khả dụng và giữ chỗ nguyên liệu khi gọi. Người chơi nấu → bưng → phục vụ trước khi khách hết kiên nhẫn. Khách ăn xong trả tiền, có thể boa. Khách hết kiên nhẫn làm giảm uy tín.
- Hai buổi chơi được riêng và nối nhau qua hai tiến trình headless dùng chung file kho. Điều khiển gợi ý là WASD hoặc phím mũi tên để bơi/đi, E để tương tác và Space để bắt cá. HUD tối thiểu cho biết thời gian, oxy, Máu, giỏ ở buổi sáng và kho khả dụng, món gọi, kiên nhẫn, trạng thái bếp, món trên tay, tiền và uy tín ở buổi tối.

## 3. Cảm giác và phong cách
Sông nước màu phù sa, bờ dừa nước, nhà sàn và ánh hồng buổi sớm. Tối có đèn dây vàng và khói bếp. Út Sen mặc áo bà ba, buộc khăn rằn, đeo kính lặn tự chế và giỏ lưới. Dùng mặt cắt nhìn ngang cho cảnh lặn và góc nhìn từ trên xuống cho nhà bè. Có thể bắt đầu bằng hình khối 2D. Giọng Nam Bộ trong thoại được khuyến khích. Tôn trọng văn hóa địa phương, dùng tài sản có quyền sử dụng và ghi nguồn trong CREDITS.md.

## 4. Công nghệ và cách vào lab
Starter Python: `chonoi/`. Test contract v1.0 độc lập với ngôn ngữ.
- Fork repo về tài khoản cá nhân, thêm collaborator, public repo.
- Điền `TEAM.md`, khớp `team_size` trong `game.contract.json`.

## 5. Nguyên liệu và món
- Nguyên liệu:
  - `ca_loc`: Cá lóc
  - `ca_linh`: Cá linh
  - `bong_dien_dien`: Bông điên điển
  - `bong_sung`: Bông súng
- Món:
  - `ca_loc_nuong_trui`: Cá lóc nướng trui (recipe: `ca_loc × 1`, cook: 6s, price: 60)
  - `goi_bong_sung`: Gỏi bông súng (recipe: `bong_sung × 2`, cook: 4s, price: 40)
  - `lau_ca_linh_dien_dien`: Lẩu cá linh bông điên điển (recipe: `ca_linh × 3 + bong_dien_dien × 1`, cook: 10s, price: 120)

## 6. Bốn lát làm song song (Lõi kỹ thuật)
- **Lát 1:** Bơi, oxy, ngạt, Máu, ngất, chặn biên, giỏ (LIFO). (`chonoi/sim/gather.py`)
- **Lát 2:** Hái nút nổi, bắt cá dưới nước, cập bến, ghi file kho. (`chonoi/sim/gather.py`)
- **Lát 3:** Khách đến theo lịch, chọn món đủ nguyên liệu, giữ chỗ nguyên liệu, kiên nhẫn, rời quán, no_dish. (`chonoi/sim/quan.py`)
- **Lát 4:** Bếp nấu, hoàn thành, bưng món lên tay, phục vụ bàn, khách ăn, trả tiền, boa, uy tín, hết ca. (`chonoi/sim/quan.py`)

## 7. Định nghĩa hoàn thành (DoD)
- Chơi được cả hai buổi, đúng phạm vi lõi. HUD đọc được trong lúc chơi.
- `game.contract.json` khớp bản chạy và đầy đủ Test Contract v1.0. Smoke hai tiến trình trên main cho thấy quán nhận đúng file kho.
- `README.md` ghi cách chạy sạch tối đa 3 lệnh, điều khiển, cách tính điểm và lệnh test.
- `TEAM.md` có danh sách và thỏa thuận nhóm. `team_size` khớp danh sách.
- Hợp đồng kho đã thống nhất, có schema và ví dụ hợp lệ.
- Có `docs/verification/phase-1.md` và bằng chứng chạy ở commit gắn tag trong `docs/proof/phase-1/`. Đã cập nhật ghi chép tối thiểu.
- Đẩy tag `phase-1` trỏ tới commit bàn giao trên main.
