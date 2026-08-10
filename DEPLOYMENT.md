# Thông Tin Deploy — Checkpoint 5

## Thông Tin Học Viên

| Mục | Nội dung |
|-----|----------|
| Họ và tên | Nguyễn Đức Anh |
| Mã học viên | 2A202601063 |
| Repo | https://github.com/DucAnhIT03/Day12_2A202601063_NguyenDucAnh |

## Service

| Mục | Nội dung |
|-----|----------|
| URL kiểm tra | http://localhost:8000 |
| Platform | Railway được thử trước; bằng chứng nộp dùng Local Fallback với Docker Compose |
| Ngày kiểm tra | 2026-08-10 |
| Topology | Nginx → 3 agent replica → Redis |

## Biến Môi Trường

Chỉ liệt kê tên và nguồn, không lưu giá trị khóa trong tài liệu hoặc Git:

| Biến | Trạng thái | Nguồn |
|------|-----------|-------|
| `PORT` | ✅ | 8000 trong môi trường local |
| `AGENT_API_KEY` | ✅ | file `.env` bị Git ignore |
| `REDIS_URL` | ✅ | service Redis trong Docker Compose |
| `RATE_LIMIT_PER_MINUTE` | ✅ | 10 |
| `MONTHLY_BUDGET_USD` | ✅ | 10.0 |
| `LOG_LEVEL` | ✅ | INFO |
| `LOCAL_FALLBACK` | ✅ | true |

## Kết Quả Chạy Thật

Các lệnh được gọi qua Nginx tại `http://localhost:8000`:

```text
GET  /health                 → 200 {"status":"ok","service":"day12-agent","version":"1.0.0"}
GET  /ready                  → 200 {"status":"ready","redis":true}
POST /ask không có API key   → 401 Unauthorized
POST /ask có API key hợp lệ  → 200, user_id=cp5-evidence, history_length=0
```

Kiểm tra stateless qua năm request cùng user:

```text
replicas=3
history_lengths=0,2,4,6,8
agent-1 handled=1
agent-2 handled=2
agent-3 handled=2
```

## Bằng Chứng

- `screenshots/dashboard.png`: Docker Compose Local Fallback với Redis, ba agent replica và Nginx đều hoạt động.
- `screenshots/health.png`: `GET /health` trả HTTP 200 (liveness).
- `screenshots/ready.png`: `GET /ready` trả HTTP 200 và xác nhận Redis sẵn sàng.
- `screenshots/ask-unauthorized.png`: `POST /ask` không có `X-API-Key` trả HTTP 401.
- `screenshots/ask-authorized.png`: `POST /ask` có API key hợp lệ trả HTTP 200; khóa thật đã được che.
- `screenshots/stateless.png`: năm request được xử lý qua ba replica với lịch sử dùng chung trong Redis.

## Lý Do Dùng Local Fallback

Railway chuyển tới GitHub OAuth nhưng phiên deploy không có đăng nhập GitHub;
Chrome có phiên người dùng cũng không khả dụng. Không có credential an toàn để
hoàn tất bước kết nối repository, nên bài dùng phương án Local Fallback được
cho phép. Docker image vẫn được build thành công và stack local đã được kiểm
tra qua Nginx.
