# Lab 4 — Phân tích kết quả Load Testing

## Bảng tổng hợp số liệu đo thực tế

| Kịch bản | Users | Spawn rate | Duration | p95 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|
| **A (Baseline)** | 10 | 2 | 30s | **19 ms** | 0.00% | 4.76 |
| **B (Load test)** | 50 | 5 | 60s | **23 ms** | 0.36% | 23.30 |
| **C (Spike test)** | 200 | 50 | 30s | **360 ms** | 0.21% | 94.11 |

---

## Trả lời các câu hỏi phân tích

### 1. Kịch bản có p95 cao nhất là gì? Dùng số liệu quan sát để giải thích.
- **Kịch bản có p95 cao nhất:** **Kịch bản C** với $p95 = \mathbf{360\text{ ms}}$ (so với $19\text{ ms}$ ở Kịch bản A và $23\text{ ms}$ ở Kịch bản B).
- **Giải thích:**
  - Kịch bản C mô phỏng một đợt tăng tải đột ngột (Spike test): 200 người dùng được khởi tạo với tốc độ 50 users/giây (chỉ mất ~4 giây để đạt tải tối đa), đẩy lưu lượng truy vấn lên tới **94.11 RPS** (2,799 requests trong 30 giây).
  - Flask development server (Werkzeug WSGI) chạy ở chế độ đơn tiến trình đa luồng (single process multithreaded) và SQLite là cơ sở dữ liệu file cục bộ có cơ chế khóa (file-level lock) khi ghi.
  - Khi 200 users đồng thời gửi request, hàng đợi socket của hệ điều hành và thread pool của ứng dụng bị bão hòa (thread contention & I/O bottleneck). Thời gian chờ (queueing delay) trước khi request được xử lý tăng vọt, khiến độ trễ ở các phân vị cao tăng phi tuyến tính ($p90 = 100\text{ ms}$, $p95 = 360\text{ ms}$, $p98 = 710\text{ ms}$, $p99 = 790\text{ ms}$, Max lên tới $890\text{ ms}$).

### 2. Endpoint nào tăng failure rate? Phân biệt lỗi HTTP thực và lỗi đánh dấu trong Locust.
- **Quan sát từ báo cáo Locust:**
  - Trong Kịch bản B ghi nhận 5 fails ($0.36\%$) và Kịch bản C ghi nhận 6 fails ($0.21\%$). Tất cả các lỗi này đều xảy ra ở endpoint `GET /books?year=[year]`.
- **Phân biệt bản chất lỗi:**
  - **Lỗi đánh dấu trong Locust (Client-side artificial failure):** Đây **không phải** là lỗi do backend Flask phát sinh (server thực tế vẫn trả về HTTP 200). Đây là lỗi do code `locustfile.py` chủ động gắn nhãn thất bại:
    ```python
    if random.random() < 0.01:
        response.failure("Simulated 500: Artificial internal server error (1% injected failure)")
    ```
    Tỉ lệ này được tiêm vào cố định ở mức ~1% của riêng task tìm kiếm theo năm để mô phỏng lỗi mạng hoặc dependency bên ngoài, hoàn toàn độc lập với tải hệ thống.
  - **Lỗi HTTP thực tế (Server-side failure):** Endpoint có nguy cơ phát sinh lỗi thực tế cao nhất khi concurrency tăng là `POST /books`. Do `POST /books` thực hiện ghi vào SQLite (`db.session.commit()`), nếu nhiều request ghi đồng thời cạnh tranh khóa và vượt quá timeout khóa của SQLite (5 giây), SQLite sẽ phát sinh ngoại lệ `OperationalError: database is locked` trả về HTTP 500 thực sự.

### 3. Với SLO giả định p95 < 300 ms, kịch bản nào đạt? Nêu giới hạn của phép đo và đề xuất baseline cho CI gate.
- **Đánh giá theo SLO ($p95 < 300\text{ ms}$):**
  - **Kịch bản A (10 users):** $p95 = 19\text{ ms} < 300\text{ ms} \rightarrow$ **ĐẠT** (hiệu năng xuất sắc).
  - **Kịch bản B (50 users):** $p95 = 23\text{ ms} < 300\text{ ms} \rightarrow$ **ĐẠT**.
  - **Kịch bản C (200 users spike):** $p95 = 360\text{ ms} > 300\text{ ms} \rightarrow$ **KHÔNG ĐẠT** ($p95$ vượt ngưỡng cho phép 20%, $p99$ lên tới $790\text{ ms}$).
- **Giới hạn của phép đo:**
  - Thử nghiệm được thực hiện trên môi trường phát triển (Flask development server + SQLite file) trên máy cá nhân (`localhost`), nơi client (Locust) và server cùng chia sẻ tài nguyên CPU/RAM và không có độ trễ mạng Internet thực tế. Do đó, kết quả này chỉ mang tính so sánh tương đối giữa các kịch bản, không phản ánh chính xác năng lực chịu tải trên môi trường Production (thường dùng Gunicorn/uWSGI + PostgreSQL + reverse proxy Nginx).
- **Đề xuất baseline cho CI gate (Performance Quality Gate):**
  - Không nên chạy Kịch bản C trong CI do tốn tài nguyên và runner CI thường yếu, dễ gây false-negative.
  - **Kịch bản khuyến nghị trong CI:** Chạy baseline Kịch bản B thu nhỏ (ví dụ 30 users, duration 20s).
  - **Ngưỡng kiểm soát (Quality Gate Thresholds):**
    - $p95 \le 150\text{ ms}$ (đặt ngưỡng chặt chẽ trong CI để đảm bảo biên an toàn cho SLO 300ms ở production).
    - Tỉ lệ lỗi HTTP thực tế (5xx từ server) $= 0\%$.
    - Throughput tối thiểu $\ge 25\text{ RPS}$.
  - Nếu build CI vượt quá các ngưỡng trên, pipeline sẽ tự động ngắt và từ chối merge code.

### 4. Câu hỏi bonus: Nếu connection pool bị giới hạn ở 5, điều gì xảy ra khi 200 user truy cập đồng thời? Làm thế nào để kiểm chứng bằng Locust?
- **Hiện tượng xảy ra:**
  - Khi connection pool bị giới hạn ở 5 và có 200 user gửi request đồng thời: Tối đa chỉ có 5 request được cấp kết nối để truy vấn cơ sở dữ liệu. 195 request còn lại sẽ bị đẩy vào hàng đợi của pool (`QueuePool`).
  - Hàng đợi này có thời gian chờ tối đa quy định bởi `pool_timeout` (mặc định là 30 giây trong SQLAlchemy).
  - Khi hàng đợi bị đầy hoặc thời gian chờ của một request vượt quá `pool_timeout`, SQLAlchemy sẽ ném ra ngoại lệ:
    `sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 0 reached, connection timed out, timeout 30.00`
  - Ứng dụng Flask sẽ trả về mã lỗi **HTTP 500 Internal Server Error** cho client.
  - Thời gian phản hồi ($p95$, $p99$, Max) của các request bị xếp hàng sẽ tăng vọt lên xấp xỉ ngưỡng `pool_timeout`.
- **Cách kiểm chứng bằng Locust:**
  1. Trong file cấu hình của Flask app, cấu hình giới hạn pool:
     ```python
     app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
         "pool_size": 5,
         "max_overflow": 0,
         "pool_timeout": 5  # Đặt timeout ngắn (5s) để nhanh chóng quan sát được lỗi
     }
     ```
  2. Chạy Kịch bản C trong Locust:
     ```bash
     locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 -u 200 -r 50 -t 30s --html reports/pool_test.html
     ```
  3. Mở file báo cáo `reports/pool_test.html` để kiểm chứng:
     - Tỉ lệ lỗi **Failure rate** tăng đột biến lên mức cao.
     - Trong bảng **Failures / Exceptions**, xuất hiện lỗi: `500 Server Error: TimeoutError: QueuePool limit of size 5...`.
     - Biểu đồ phân vị độ trễ hiển thị thời gian phản hồi chạm trần tại mốc ~5,000 ms (`pool_timeout`).
