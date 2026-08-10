"""CP4 — Graceful shutdown.

Khi bạn deploy phiên bản mới, orchestrator (Docker, Railway, Cloud Run, K8s)
gửi **SIGTERM** rồi đợi vài chục giây trước khi SIGKILL. Nếu app bỏ qua tín
hiệu đó, mọi request đang xử lý dở bị cắt giữa chừng — user thấy lỗi 502 mỗi
lần bạn deploy.

Ứng xử đúng: nhận SIGTERM → báo "tôi sắp tắt" qua health check để load
balancer ngừng đẩy traffic mới vào → xử lý nốt request đang chạy → thoát.
"""

from __future__ import annotations

import signal
import threading
from contextlib import contextmanager


DRAIN_TIMEOUT_SECONDS = 30.0


class Lifecycle:
    """Giữ trạng thái vòng đời của process."""

    def __init__(self) -> None:
        self.shutting_down = False
        # Handler đã được đăng ký trước ta (của uvicorn) — xem install()
        self._previous: dict = {}
        self._installed = False
        self._active_requests = 0
        self._requests_finished = threading.Condition()

    @property
    def active_requests(self) -> int:
        """Số request đã nhận và chưa xử lý xong."""
        with self._requests_finished:
            return self._active_requests

    @contextmanager
    def track_request(self):
        """Theo dõi một request để shutdown có thể đợi nó hoàn thành."""
        with self._requests_finished:
            self._active_requests += 1
        try:
            yield
        finally:
            with self._requests_finished:
                self._active_requests -= 1
                if self._active_requests == 0:
                    self._requests_finished.notify_all()

    def wait_for_requests(self, timeout: float = DRAIN_TIMEOUT_SECONDS) -> bool:
        """Đợi request đang chạy, nhưng không quá ``timeout`` giây.

        Trả ``True`` nếu đã drain hết, ``False`` nếu chạm giới hạn thời gian.
        Việc đợi diễn ra trong lifespan shutdown, không nằm trong signal
        handler, để event loop vẫn có thể hoàn thành các request đang chạy.
        """
        with self._requests_finished:
            return self._requests_finished.wait_for(
                lambda: self._active_requests == 0,
                timeout=max(0.0, timeout),
            )

    def request_shutdown(self, signum=None, frame=None) -> None:
        """Signal handler: đánh dấu process đang tắt dần.

        TODO (CP4):
          1. ``self.shutting_down = True``
          2. Gọi lại handler cũ nếu có::

                previous = self._previous.get(signum)
                if callable(previous):
                    previous(signum, frame)

        Bước 2 quan trọng hơn vẻ ngoài của nó. Mỗi tín hiệu chỉ có **một**
        handler: đăng ký handler của mình là ghi đè handler của uvicorn — thứ
        chịu trách nhiệm thật sự cho việc dừng server. Không gọi lại nó thì
        app bật cờ "đang tắt" rồi... chạy tiếp mãi mãi, cho tới khi
        orchestrator hết kiên nhẫn và SIGKILL. Đúng cái mà graceful shutdown
        định tránh.

        Chữ ký ``(signum, frame)`` là bắt buộc vì Python gọi handler với 2
        tham số này. Không làm gì nặng ở đây (không gọi mạng, không ghi file)
        — handler chạy xen giữa bytecode.
        """
        self.shutting_down = True
        previous = self._previous.get(signum)
        if callable(previous):
            previous(signum, frame)

    def install(self) -> None:
        """Đăng ký handler cho SIGTERM và SIGINT, nhớ lại handler cũ.

        TODO (CP4): với mỗi tín hiệu trong ``(signal.SIGTERM, signal.SIGINT)``:

            self._previous[sig] = signal.getsignal(sig)   # nhớ handler cũ
            signal.signal(sig, self.request_shutdown)     # rồi mới ghi đè

        SIGTERM: orchestrator yêu cầu tắt. SIGINT: bạn bấm Ctrl+C.
        """
        if self._installed:
            return

        for sig in (signal.SIGTERM, signal.SIGINT):
            self._previous[sig] = signal.getsignal(sig)
            signal.signal(sig, self.request_shutdown)
        self._installed = True


# Một instance dùng chung cho cả app
lifecycle = Lifecycle()
