# Phiếu Phản Ánh — K3 Ngày 12

> **Bài làm cá nhân.** Các câu trả lời dưới đây dựa trên kết quả test, Docker
> image và stack ba replica mình đã chạy ngày 10/08/2026.
>
> Họ và tên: Nguyễn Đức Anh — Mã học viên: 2A202601063

---

### Câu 1 — Fail fast (CP1)

Khi deploy một phiên bản mới, nếu mình quên đặt `AGENT_API_KEY` thì Pydantic
dừng ứng dụng ngay trong startup. Nền tảng thấy bản deploy mới không healthy và
có thể tiếp tục giữ bản cũ. Nếu ứng dụng dùng mặc định `changeme`, bản lỗi vẫn
chạy bình thường; người biết key mẫu có thể gọi `/ask` và tiêu ngân sách trước
khi mình nhìn thấy lỗi. Với mình, lỗi lúc deploy dễ xử lý hơn một service "xanh"
nhưng đang mở cửa bằng khóa giả.

---

### Câu 2 — Log cho máy đọc (CP1)

Một dòng mình lấy từ container khi gọi `/ask`:

```json
{"event": "ask_completed", "level": "info", "timestamp": "2026-08-10T03:57:09.096746+00:00", "user_id": "cp4-verify-1786334228846", "tokens_in": 195, "tokens_out": 48, "cost_usd": 0.00005805}
```

Từ log này mình có thể lọc toàn bộ request của một `user_id` để điều tra sự cố,
và cộng `cost_usd` hoặc vẽ biểu đồ token theo thời gian. Dòng
`print("đã trả lời xong")` không có trường cố định nên công cụ log không biết user,
chi phí hay thời điểm để lọc và tổng hợp.

---

### Câu 3 — Kích thước image (CP2)

Mình build cả hai image trên Docker Desktop và đo bằng `docker images`:

| Bản | Dung lượng |
|-----|-----------:|
| 1 stage, `python:3.11`, `COPY . .` | 1.69 GB |
| Multi-stage, `python:3.11-slim` | 270 MB |

Phần chênh lệch khoảng 1.42 GB đến từ base image Python đầy đủ, source/test và
các thành phần phục vụ build được giữ lại trong image một stage. Runtime
multi-stage chỉ nhận dependency đã cài cùng `app/` và `utils/`, không mang toàn
bộ môi trường builder sang production.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sau khi sửa `app/main.py` và build lại, layer base, `COPY requirements.txt` và
`pip install` được lấy từ cache vì requirements không đổi. Layer copy source
ứng dụng và các layer đứng sau nó phải tạo lại. Nếu đặt `COPY . .` trước
`RUN pip install`, chỉ một ký tự trong source cũng làm layer copy đổi, kéo theo
việc cài lại toàn bộ package. Lần build kiểm tra của mình vì vậy lâu hơn nhiều
so với build multi-stage đã có cache dependency.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Nếu endpoint Python có lỗi thực thi lệnh, kẻ tấn công trước tiên nhận quyền của
process trong container. Khi process là root, họ có thể sửa file hệ thống,
khai thác mount/socket cấu hình sai hoặc kết hợp lỗ hổng kernel để tác động host
với quyền rất cao. Image của mình chạy `appuser` UID 10001, nên bước đầu tiên
chỉ cho quyền của user hạn chế. `USER appuser` không thay thế mọi biện pháp
sandbox, nhưng cắt quyền root mặc định và giảm đáng kể phạm vi thiệt hại.

---

### Câu 6 — Cửa sổ trượt (CP3)

Với fixed window 10 request/phút, user có thể gửi 10 request ở giây 59 rồi 10
request khác ngay giây 00 của phút kế tiếp: tổng cộng 20 request trong khoảng
hai giây nhưng mỗi phút lịch vẫn chỉ ghi 10. Sliding window nhìn lại đúng 60
giây gần nhất nên nhóm 10 request cũ vẫn còn trong Redis Sorted Set và nhóm
tiếp theo bị trả 429.

---

### Câu 7 — Rate limit và cost guard (CP3)

Rate limit bảo vệ tốc độ và tải hạ tầng; cost guard bảo vệ số tiền tích lũy.
Một user gửi một request mỗi phút nhưng mỗi request xử lý tài liệu 100 trang sẽ
không vi phạm tốc độ, trong khi cost guard phải chặn khi ngân sách tháng hết.
Ngược lại, user còn nguyên ngân sách và chỉ gửi câu hỏi rất ngắn nhưng bắn 11
request trong vài giây: cost guard vẫn cho phép về tiền, còn rate limiter chặn
request thứ 11.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp probe và bắt nó ping Redis, khi Redis mất kết nối cả ba container đều
trả probe lỗi. Orchestrator hiểu nhầm ba process đã chết và lần lượt restart
chúng. Redis vẫn lỗi nên các container mới tiếp tục fail, tạo restart loop và
cắt cả request đang xử lý. Khi tách probe, `/health` vẫn 200 vì process còn
sống, còn `/ready` trả 503 để load balancer tạm ngừng chuyển traffic mà không
giết container.

---

### Câu 9 — Stateless (CP4)

Mình gọi năm request qua Nginx; ba replica nhận lần lượt 2, 1 và 2 request,
nhưng `history_length` vẫn tăng `0, 2, 4, 6, 8`. Giá trị tăng hai vì lịch sử
đếm message trước request hiện tại và mỗi lượt lưu một message user cộng một
message assistant. Nếu dùng dict riêng trong từng container với vòng A, B, C,
A, B, mình sẽ thấy gần `0, 0, 0, 2, 2`: container B không thể đọc dữ liệu A
đã ghi. Redis làm cho mọi replica nhìn thấy cùng một lịch sử.

---

### Câu 10 — Deploy thật (CP5)

Mình thử Railway nhưng luồng OAuth chuyển tới trang `Sign in to GitHub` và yêu
cầu username/password; phiên trình duyệt deploy không có đăng nhập GitHub, còn
Chrome kết nối cũng không khả dụng. Mình xác định nguyên nhân bằng URL OAuth và
form đăng nhập hiển thị trước khi Railway cho tạo project, nên đây không phải
lỗi build của Dockerfile. Mình không nhập hoặc lưu credential trong công cụ tự
động; thay vào đó đặt `LOCAL_FALLBACK=true`, chạy ba agent sau Nginx cùng Redis,
rồi kiểm tra thực tế `/health=200`, `/ready=200`, thiếu key trả 401 và đúng key
trả 200. Khi có phiên GitHub hợp lệ, mình có thể tiếp tục Railway mà không cần
sửa image.
