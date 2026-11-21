# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| Phase 1 | Nguyễn Tuấn Dũng | Antigravity / Gemini 3.8 Flash | Lập kế hoạch Phase 1, cài đặt cơ chế Oxy, Ngạt, Máu & Ngất (Lát 1) trong `gather.py` | ~15k tokens | Ban đầu test thiếu tick để bơi ngược lên mặt nước do thời gian giảm tốc (ramp); đã chỉnh số tick test phù hợp. |
| Phase 1 | Nguyễn Tuấn Dũng | Antigravity / Gemini 3.8 Flash | Cài đặt Hái cây, Bắt cá, sức chứa giỏ (Lát 2) trong `gather.py` và chú thích hướng dẫn Lát 3/4 trong `quan.py` | ~12k tokens | Không có lỗi logic, tuân thủ đúng Test Contract và độ ưu tiên id nhỏ hơn khi hòa khoảng cách. |
