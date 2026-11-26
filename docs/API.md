# Neuro Studio — Đặc tả API Xác thực & Hợp đồng Giao diện Module

> Tài liệu này là **hợp đồng chung (contract)** cho các nhóm phát triển song song từ **Tuần 2 đến Tuần 5**.  
> Mọi module (`auth_routes`, `user_repository`, `auth_service`, `ownership`, `read_routes`, `write_routes`, Frontend) phải tuân thủ chính xác chữ ký hàm, trường dữ liệu và mã lỗi dưới đây để có thể kiểm thử độc lập bằng `mock/fake` và ghép nối trơn tru khi tích hợp.

---

## 1. Quy ước chung

- **Base path:** `/api/v1`
- **Content-Type:** `application/json; charset=utf-8`
- **Cơ chế phiên (Session / Token):**
  - Cookie phiên `HttpOnly; SameSite=Strict; Path=/` lưu token phiên đã ký (hoặc session ID ngẫu nhiên lưu DB/HMAC token) kết hợp header `Authorization: Bearer <token>` (tùy chọn cho kiểm thử HTTP client) và header chống CSRF `X-NeuroStudio` khi dùng cookie trên trình duyệt.
  - Thời hạn phiên mặc định: **24 giờ** (`86400` giây), có thể cấu hình qua biến môi trường hoặc tham số khởi tạo `AuthService`.
- **Định dạng lỗi thống nhất:**
  ```json
  {
    "code": "ERROR_CODE",
    "detail": "Mô tả lỗi ngắn gọn, rõ ràng cho người dùng."
  }
  ```
- **Bảo mật bắt buộc:**
  - Không bao giờ lưu mật khẩu dạng văn bản thường; không trả `password_hash` trong bất kỳ response nào; không ghi mật khẩu vào log.
  - Chuẩn hóa `username` (trim khoảng trắng, kiểm tra định dạng) và `email` (trim + lowercase) trước khi lưu hoặc truy vấn.

---

## 2. Đặc tả HTTP API Xác thực (`/api/v1/auth/*`)

### 2.1. Đăng ký tài khoản — `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "username": "nguyen_van_a",
  "email": "a@example.com",
  "password": "StrongPassword123!",
  "display_name": "Nguyễn Văn A"
}
```

**Quy tắc kiểm tra đầu vào:**
- `username`: chuỗi `3–32` ký tự, khớp `^[a-zA-Z0-9_.-]+$`, duy nhất (không phân biệt hoa/thường khi so trùng).
- `email`: định dạng email hợp lệ, tối đa `254` ký tự, duy nhất sau khi lowercase.
- `password`: tối thiểu `8` ký tự, tối đa `128` ký tự, không chỉ gồm khoảng trắng.
- `display_name`: tùy chọn (mặc định bằng `username`), tối đa `80` ký tự.

**Response thành công — `201 Created`:**
```json
{
  "user": {
    "id": "usr_01J...",
    "username": "nguyen_van_a",
    "email": "a@example.com",
    "display_name": "Nguyễn Văn A",
    "created_at": 1764200000.0
  },
  "access_token": "<opaque-or-signed-token>",
  "token_type": "bearer",
  "expires_at": 1764286400.0
}
```
*(Kèm `Set-Cookie` nếu thiết lập đăng nhập ngay sau khi đăng ký, hoặc trả thông tin user + token để client lưu phiên nhất quán.)*

**Mã lỗi:**
| HTTP | `code` | Khi nào xảy ra |
|---|---|---|
| `400` / `422` | `VALIDATION_ERROR` | Thiếu trường, mật khẩu quá ngắn, `username`/`email` sai định dạng. |
| `409` | `USER_ALREADY_EXISTS` | `username` hoặc `email` đã tồn tại trong hệ thống. |

---

### 2.2. Đăng nhập — `POST /api/v1/auth/login`

**Request Body:**
```json
{
  "identifier": "nguyen_van_a",
  "password": "StrongPassword123!"
}
```
*(Trường `identifier` chấp nhận `username` hoặc `email`.)*

**Response thành công — `200 OK`:**
```json
{
  "user": {
    "id": "usr_01J...",
    "username": "nguyen_van_a",
    "email": "a@example.com",
    "display_name": "Nguyễn Văn A",
    "created_at": 1764200000.0
  },
  "access_token": "<opaque-or-signed-token>",
  "token_type": "bearer",
  "expires_at": 1764286400.0
}
```
*(Đồng thời set cookie phiên `HttpOnly; SameSite=Strict`.)*

**Mã lỗi:**
| HTTP | `code` | Khi nào xảy ra |
|---|---|---|
| `400` / `422` | `VALIDATION_ERROR` | Thiếu `identifier` hoặc `password`. |
| `401` | `INVALID_CREDENTIALS` | Không tìm thấy tài khoản hoặc sai mật khẩu (trả cùng một thông báo để tránh lộ tài khoản tồn tại). |

---

### 2.3. Lấy thông tin người dùng hiện tại — `GET /api/v1/auth/me`

**Yêu cầu:** Có phiên hợp lệ (cookie phiên hoặc header `Authorization: Bearer <token>`).

**Response thành công — `200 OK`:**
```json
{
  "user": {
    "id": "usr_01J...",
    "username": "nguyen_van_a",
    "email": "a@example.com",
    "display_name": "Nguyễn Văn A",
    "created_at": 1764200000.0
  },
  "expires_at": 1764286400.0
}
```

**Mã lỗi:**
| HTTP | `code` | Khi nào xảy ra |
|---|---|---|
| `401` | `AUTH_REQUIRED` | Không gửi thông tin xác thực. |
| `401` | `TOKEN_INVALID` | Token sai chữ ký hoặc không hợp lệ. |
| `401` | `TOKEN_EXPIRED` | Phiên/token đã hết hạn hoặc đã đăng xuất. |

---

### 2.4. Đăng xuất — `POST /api/v1/auth/logout`

**Yêu cầu:** Có phiên hợp lệ (và header CSRF khi dùng cookie).

**Response thành công — `200 OK`:**
```json
{
  "logged_out": true
}
```
*(Xóa cookie phiên trên trình duyệt và thu hồi token/phiên hiện tại nếu có bảng phiên.)*

---

## 3. Quy ước phân quyền tài nguyên (Áp dụng ở T4–T5)

| Tình huống | HTTP | `code` |
|---|---|---|
| Chưa đăng nhập truy cập tài nguyên bảo vệ | `401` | `AUTH_REQUIRED` |
| Đã đăng nhập nhưng truy cập/sửa/xóa tài nguyên của người khác | `403` | `FORBIDDEN_RESOURCE` |
| Tài nguyên không tồn tại | `404` | `NOT_FOUND` |
| Tài nguyên cũ chưa có `owner_id` (`NULL`) | Theo chính sách Core | Không tự gán chủ sở hữu ngẫu nhiên; chỉ đọc/xử lý theo quy tắc thống nhất với Core trong T4. |

**Danh sách API ưu tiên áp dụng phân quyền (T5):**
- **Nhóm đọc (`read_routes`):**
  - `GET /api/v1/projects` (chỉ liệt kê dự án thuộc `current_user.id`)
  - `GET /api/v1/projects/{id}`
  - `GET /api/v1/projects/{id}/versions`
  - `GET /api/v1/projects/{id}/backup`
  - `GET /api/v1/project-trash`
  - `GET /api/v1/runs`, `GET /api/v1/runs/{id}` (lọc theo quyền sở hữu)
- **Nhóm ghi (`write_routes`):**
  - `POST /api/v1/projects` (tự gán `owner_id = current_user.id`, bỏ qua mọi `owner_id` từ client)
  - `PUT /api/v1/projects/{id}`
  - `DELETE /api/v1/projects/{id}`
  - `POST /api/v1/projects/{id}/clone`
  - `POST /api/v1/project-trash/{id}/restore`
  - `POST /api/v1/runs` (chỉ chạy trên dự án thuộc `current_user.id`)

---

## 4. Hợp đồng giao diện Python nội bộ (Cho nhóm T2–T5 làm song song)

Các nhóm ở T2 và T4 bám theo giao diện dưới đây (có thể đặt tại `src/neurostudio/auth/contracts.py` hoặc dùng `Protocol` tương đương khi mock):

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UserRecord:
    id: str
    username: str
    email: str
    display_name: str
    password_hash: str
    created_at: float


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    username: str
    email: str
    display_name: str
    expires_at: float


class DuplicateUserError(Exception):
    """Ném ra khi username hoặc email đã tồn tại."""


class AuthError(Exception):
    """Lỗi xác thực có kèm mã lỗi chuẩn (AUTH_REQUIRED, TOKEN_INVALID, TOKEN_EXPIRED, INVALID_CREDENTIALS)."""
    def __init__(self, code: str, detail: str, status_code: int = 401):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class UserRepository(Protocol):
    def create_user(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        display_name: str,
    ) -> UserRecord: ...

    def get_by_id(self, user_id: str) -> UserRecord | None: ...

    def get_by_username(self, username: str) -> UserRecord | None: ...

    def get_by_email(self, email: str) -> UserRecord | None: ...

    def get_by_identifier(self, identifier: str) -> UserRecord | None: ...


class AuthService(Protocol):
    def hash_password(self, plain_password: str) -> str: ...

    def verify_password(self, plain_password: str, password_hash: str) -> bool: ...

    def issue_token(self, user: UserRecord) -> tuple[str, float]: ...

    def verify_token(self, token: str) -> AuthenticatedUser: ...

    def revoke_token(self, token: str) -> None: ...


class OwnershipRepository(Protocol):
    def get_owner_id(self, resource_type: str, resource_id: str) -> str | None: ...

    def list_owned_ids(self, resource_type: str, owner_id: str) -> list[str]: ...

    def assign_owner(self, resource_type: str, resource_id: str, owner_id: str) -> None: ...
```

### Lưu ý khi viết Mock/Fake cho Unit Test
- **Router đăng ký/đăng nhập (T2):** nhận `user_repo: UserRepository` và `auth_service: AuthService` qua FastAPI dependency injection (`Depends`) để test dễ dàng thay bằng `InMemoryUserRepository` và `FakeAuthService`.
- **CSDL tài khoản (T2):** triển khai `SQLiteUserRepository` chạy trên `tmp_path / "studio.db"` độc lập, không cần khởi tạo FastAPI app.
- **Dịch vụ xác thực (T2):** dùng thuật toán băm mật khẩu mạnh có salt (ví dụ `hashlib.scrypt` có sẵn trong thư viện chuẩn Python 3.12 — không cần thêm dependency ngoài làm lệch `uv.lock`!) và ký token bằng HMAC-SHA256 kèm `exp` + `jti` (hoặc bảng session trong SQLite).
- **Phân quyền sở hữu (T4):** cung cấp FastAPI dependency `require_resource_owner(resource_type)` kiểm tra `current_user.id == owner_id`, trả `401` nếu chưa đăng nhập, `404` nếu không tìm thấy, `403 FORBIDDEN_RESOURCE` nếu khác chủ sở hữu.
