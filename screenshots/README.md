# Minh chứng Checkpoint CP5

Bài nộp sử dụng phương án `LOCAL_FALLBACK=true` được đề bài cho phép. Các ảnh được
ghi nhận từ Docker Compose và các request thật gọi qua Nginx tại
`http://localhost:8000` ngày 2026-08-10.

| File | Minh chứng |
|------|------------|
| `dashboard.png` | Redis, ba agent replica và Nginx đang hoạt động |
| `health.png` | `/health` trả HTTP 200 |
| `ready.png` | `/ready` trả HTTP 200, Redis sẵn sàng |
| `ask-unauthorized.png` | `/ask` thiếu API key trả HTTP 401 |
| `ask-authorized.png` | `/ask` có API key hợp lệ trả HTTP 200; key đã được che |
| `stateless.png` | Request được phân phối qua ba replica và dùng chung lịch sử Redis |

Không có giá trị `AGENT_API_KEY` nào xuất hiện trong ảnh hoặc repository.
