# Hướng dẫn cài đặt và chạy dự án cục bộ (SETUP)

> Hướng dẫn dành cho thành viên/CTV phát triển Neuro Studio trên **Windows** và **Linux (x86-64)**.

---

## 1. Yêu cầu môi trường

| Công cụ | Phiên bản yêu cầu | Ghi chú |
|---|---|---|
| **Git** | Mới nhất | Bắt buộc để clone/branch/PR |
| **Python** | `3.12` (`>=3.12,<3.13`) | `uv` có thể tự tải CPython 3.12 nếu máy đang dùng bản Python khác |
| **uv** | `0.7.8` (khuyến nghị) | Quản lý virtual environment và cài package từ `uv.lock` |
| **Node.js & npm** | Node.js `22` (hoặc mới hơn tương thích) | Chỉ cần khi phát triển/build Frontend (`apps/web`) |
| **GitHub CLI (`gh`)** | Tùy chọn | Hữu ích để mở PR và xem CI nhanh từ terminal |

> **Lưu ý:** Nếu máy bạn chưa cài `uv`, bạn có thể cài toàn cục (xem trang chính thức Astral `uv`) hoặc dùng trực tiếp script bootstrap của repo (`.tools/uv` được tự động bỏ qua bởi `.gitignore`).

---

## 2. Clone và cài đặt dependencies

### Bước 1: Clone repository
```bash
git clone https://github.com/maithedung79/NeuroStudio-LAILA.git
cd NeuroStudio-LAILA
```

### Bước 2: Đồng bộ môi trường Python (Backend + Engine + Dev tools)
```bash
uv sync --extra engine --extra dev --locked
```
Lệnh này tự tạo `.venv/` với Python `3.12` và cài chính xác các phiên bản khóa trong `uv.lock`:
- **Core:** `fastapi==0.115.12`, `pydantic==2.11.5`, `uvicorn==0.34.2`, `psutil==7.0.0`
- **Engine (CPU/Tabular):** `numpy==2.2.6`, `pandas==2.2.3`, `scikit-learn==1.6.1`, `pillow==11.2.1`, `safetensors==0.5.3`
- **Dev:** `pytest==8.3.5`, `httpx==0.28.1`, `ruff==0.11.10`, `build==1.2.2.post1`

*(Tùy chọn — chỉ cần nếu bạn làm việc trực tiếp với mô hình PyTorch hoặc UMAP:)*
```bash
# Cài thêm UMAP / analysis
uv sync --extra engine --extra analysis --extra dev --locked

# Cài thêm PyTorch CPU (tải lớn hơn)
uv pip install -r src/neurostudio/torch-cpu.lock --require-hashes
```

### Bước 3: Cài đặt dependencies Frontend (`apps/web`)
```bash
npm ci --prefix apps/web --no-audit --no-fund
```

---

## 3. Chạy ứng dụng để phát triển

### Chế độ 1: Chạy toàn bộ qua Backend (dùng bản Frontend đã build sẵn)
```bash
# Build lại Frontend nếu bạn có sửa code trong apps/web/src/
npm run build --prefix apps/web

# Khởi chạy Neuro Studio trên http://127.0.0.1:8765
uv run --no-sync neurostudio
```
Tham số hữu ích cho developer:
```bash
# Không tự mở trình duyệt và dùng thư mục dữ liệu thử nghiệm riêng
uv run --no-sync neurostudio --no-browser --port 8765 --data-dir ./.tmp-workspace
```

### Chế độ 2: Phát triển Frontend có Hot-Reload (Vite dev server)
Mở **2 terminal song song**:
- **Terminal 1 (Backend API trên cổng 8765):**
  ```bash
  uv run --no-sync neurostudio --no-browser --port 8765 --data-dir ./.tmp-workspace
  ```
- **Terminal 2 (Vite dev server, tự proxy `/api` sang `127.0.0.1:8765`):**
  ```bash
  npm run dev --prefix apps/web
  ```

---

## 4. Checklist kiểm tra trước khi mở Pull Request

Chạy đủ các lệnh sau tại thư mục gốc repo (giống hệt những gì `.github/workflows/ci.yml` chạy):

```bash
# 1. Kiểm tra lint Python (Ruff)
uv run --no-sync ruff check src tests

# 2. Chạy toàn bộ bộ kiểm thử Backend (Pytest)
uv run --no-sync pytest -v

# 3. Kiểm tra CLI entrypoint
uv run --no-sync neurostudio --help

# 4. Kiểm tra kiểu TypeScript & build Frontend (nếu có sửa apps/web)
npm run build --prefix apps/web
```

> **Lưu ý trên Windows về `src/neurostudio/static/`:** Khi chạy `npm run build` mà bạn không sửa code Frontend, Git có thể hiện cảnh báo đổi ký tự xuống dòng `LF/CRLF` trong `src/neurostudio/static/`. Nếu bạn chỉ làm Backend và không đụng `apps/web/`, hãy hoàn tác file static trước khi commit:
> ```bash
> git checkout -- src/neurostudio/static/
> ```

---

## 5. Khắc phục nhanh một số lỗi thường gặp

| Lỗi gặp phải | Nguyên nhân & Cách xử lý |
|---|---|
| `No interpreter found for Python >=3.12,<3.13` | Dùng `uv sync --extra engine --extra dev --locked` để `uv` tự tải CPython 3.12 về quản lý độc lập. |
| `Neuro Studio đang chạy với thư mục này` | Đang có một tiến trình Neuro Studio khác giữ `workspace.lock`. Tắt cửa sổ cũ hoặc truyền `--data-dir <thư-mục-khác>`. |
| `403 LOCAL_ONLY` khi gọi API bằng `TestClient` | Middleware yêu cầu `Host` là loopback. Trong `pytest`, khởi tạo `TestClient(app, base_url="http://127.0.0.1")`. |
| `401 SESSION_REQUIRED` hoặc `403 CSRF_REJECTED` | Cần gọi `GET /api/v1/session` để lấy cookie `neuro_session` và gửi kèm header `X-NeuroStudio: <token>` cho các request `POST`/`PUT`/`DELETE`. |
| `git add` báo file bị ignore | Kiểm tra `.gitignore` (thư mục gốc repo chỉ whitelist `src/`, `tests/`, `docs/`, `apps/`, `assets/`, `scripts/`, `packaging/`, `.github/`). |
