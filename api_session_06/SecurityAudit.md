# Security Audit Report
**Scope:** `POST /auth/login`, `POST /auth/refresh`, `GET /posts/{id}`

Dưới đây là danh sách ≥ 5 điểm có thể gây rò rỉ dữ liệu hoặc lỗ hổng bảo mật trên các endpoints hiện tại, kèm theo nguy cơ và hướng khắc phục:

## 1. Brute Force & Credential Stuffing (`POST /auth/login`)
* **Mô tả:** Nếu endpoint đăng nhập không có cơ chế giới hạn tỷ lệ (Rate Limiting) hoặc Captcha, kẻ tấn công có thể sử dụng tool tự động để thử hàng ngàn mật khẩu (Brute force) hoặc sử dụng danh sách email/password rò rỉ từ các trang khác (Credential Stuffing).
* **Nguy cơ:** Tài khoản người dùng bị chiếm đoạt hàng loạt (Account Takeover).
* **Khắc phục:** Triển khai Rate Limiting (giới hạn số lần thử trên mỗi IP/Email), tự động khóa tài khoản tạm thời sau N lần sai (Account Lockout) và cân nhắc áp dụng reCAPTCHA/Turnstile.

## 2. Rò rỉ Refresh Token qua XSS (`POST /auth/login` & `POST /auth/refresh`)
* **Mô tả:** Nếu Refresh Token được API trả về dưới dạng JSON và Client (Frontend) lưu trữ nó trong `localStorage` hoặc `sessionStorage`, token này có thể bị đánh cắp nếu trang web dính lỗ hổng XSS (Cross-Site Scripting).
* **Nguy cơ:** Kẻ tấn công lấy được Refresh Token và có thể tự động sinh ra Access Token mới, duy trì quyền truy cập lâu dài.
* **Khắc phục:** API nên thiết lập trả về Refresh Token thông qua `HttpOnly`, `Secure`, `SameSite=Strict` Cookie thay vì trả trong body response. 

## 3. Lỗ hổng IDOR (Insecure Direct Object Reference) (`GET /posts/{id}`)
* **Mô tả:** Mặc dù API có kiểm tra xác thực (401), nhưng nếu không kiểm tra quyền phân quyền (Authorization) ở cấp độ bản ghi (Row-level security), người dùng A có thể truyền ID bài viết riêng tư hoặc bài viết nháp của người dùng B vào endpoint này.
* **Nguy cơ:** Rò rỉ dữ liệu riêng tư, nội dung bài viết không công khai của người khác.
* **Khắc phục:** Cần kiểm tra logic ở Backend: Nếu bài viết không phải là "Public", phải xác minh xem `userId` giải mã từ Access Token có quyền xem bài viết đó không (ví dụ: có phải là tác giả hoặc bạn bè được chia sẻ không). Trả về mã lỗi 403 Forbidden nếu không có quyền.

## 4. Lộ thông tin nhạy cảm của Tác giả (Data Exposure) (`GET /posts/{id}`)
* **Mô tả:** Trong response của bài viết, Object `author` (hoặc thông tin đi kèm từ quan hệ database) có thể vô tình bị `SELECT *` và trả về toàn bộ dữ liệu, bao gồm cả số điện thoại, email cá nhân, mật khẩu băm (password hash), hoặc lịch sử trạng thái của tác giả.
* **Nguy cơ:** Rò rỉ Thông tin Định danh Cá nhân (PII) hoặc dữ liệu nhạy cảm của người dùng khác (Mass Assignment / Over-fetching).
* **Khắc phục:** Sử dụng DTO (Data Transfer Object) để map dữ liệu chuẩn xác trước khi trả về (chỉ trả về `authorId`, `authorName`, `avatarUrl`). Tuyệt đối không trả nguyên Entity model từ Database ra API.

## 5. Thiếu cơ chế Refresh Token Rotation (`POST /auth/refresh`)
* **Mô tả:** Khi sử dụng `POST /auth/refresh`, nếu Refresh Token cũ không bị vô hiệu hóa ngay lập tức sau khi đổi lấy token mới (hoặc không được lưu trạng thái cấp phát trong DB), một token bị lộ có thể được sử dụng vô thời hạn cho đến khi hết hạn (cùng lúc bởi cả nạn nhân và kẻ tấn công).
* **Nguy cơ:** Kẻ tấn công duy trì phiên đăng nhập trái phép (Session Hijacking) mà nạn nhân không hề hay biết.
* **Khắc phục:** Triển khai **Refresh Token Rotation**: Mỗi lần dùng Refresh Token để lấy token mới, Refresh Token cũ sẽ bị thu hồi và phát hành một Refresh Token mới. Nếu phát hiện một Refresh Token cũ (đã được sử dụng) bị gọi lại lần nữa, hệ thống phải lập tức thu hồi toàn bộ chuỗi token (token family) của người dùng đó (cảnh báo token theft).