# Hướng dẫn đóng góp & Quy trình Git/GitHub (CONTRIBUTING)

> Áp dụng cho toàn bộ thành viên và CTV Ban Chuyên Môn LAILA tham gia phát triển **Neuro Studio** (`https://github.com/maithedung79/NeuroStudio-LAILA`).

---

## 1. Quy tắc vàng của repository

1. **Tuyệt đối không push trực tiếp lên nhánh `main`.** Mọi thay đổi phải đi qua Pull Request (PR).
2. Nhánh `main` đang bật **Branch Protection** với 3 điều kiện bắt buộc trước khi Merge:
   - **CI xanh cả 2 môi trường:** `build (ubuntu-latest)` và `build (windows-latest)`.
   - **Đủ duyệt review:** ít nhất **1 approval** (kèm CODEOWNER `@maithedung79` theo `.github/CODEOWNERS`).
   - **Resolve hết comment:** mọi trao đổi/góp ý trên PR phải được xử lý xong.
3. **Mỗi PR chỉ giải quyết đúng 1 Issue/module.** Không sửa lan sang file của thành viên khác nếu chưa thống nhất.
4. **Không commit dữ liệu nhạy cảm hay file tạm:** không đưa mật khẩu, token, file `.env`, `.venv/`, `node_modules/`, `dist/`, hay file log lên Git.

---

## 2. Các câu lệnh Git cơ bản cho CTV

### Lần đầu tải mã nguồn về máy
```bash
git clone https://github.com/maithedung79/NeuroStudio-LAILA.git
cd NeuroStudio-LAILA
```

### Kiểm tra trạng thái & lịch sử
```bash
git status              # Xem file đang sửa / chưa stage
git branch -a           # Xem danh sách nhánh local & remote
git diff                # Xem chi tiết thay đổi chưa stage
git log --oneline -n 5  # Xem 5 commit gần nhất
```

### Quy ước đặt tên nhánh & commit
- **Tên nhánh:** `<loai>/<mo-ta-ngan>` (viết thường, không dấu, ngăn cách bằng dấu `-`)
  - `feat/auth-login-api` — tính năng mới
  - `fix/session-expiry` — sửa lỗi
  - `docs/docker-worker-rfc` — tài liệu
  - `test/auth-integration` — bổ sung kiểm thử
  - `chore/update-ci` — cấu hình, dọn dẹp
- **Commit message (Conventional Commits):**
  - `feat(auth): add register and login endpoints`
  - `test(db): add user repository migration tests`
  - `docs(api): add request/response examples for auth`
  - `fix(ui): handle expired session redirect`

---

## 3. Quy trình làm project chuẩn (6 bước)

### Bước 1: Cập nhật `main` mới nhất và tạo nhánh mới
Trước khi bắt đầu bất kỳ nhiệm vụ nào, luôn đồng bộ `main` mới nhất rồi mới rẽ nhánh:
```bash
git checkout main
git pull origin main
git checkout -b feat/ten-nhiem-vu
```
*(Nếu bạn tạo nhánh từ giao diện GitHub Web: nhớ chọn nguồn từ `main`, sau đó ở máy chạy `git fetch origin && git checkout feat/ten-nhiem-vu`.)*

### Bước 2: Làm việc theo đặc tả & tự kiểm tra trên máy
- Đọc kỹ GitHub Issue được giao, đối chiếu với `docs/API.md` và `docs/ARCHITECTURE.md`.
- Viết code sạch và viết unit test tương ứng trong thư mục `tests/`.
- Trước khi push, **bắt buộc tự chạy kiểm tra trên máy** (xem thêm `docs/SETUP.md`):
  ```bash
  # Kiểm tra lint Python
  uv run --no-sync ruff check src tests

  # Chạy toàn bộ kiểm thử Backend
  uv run --no-sync pytest -v

  # Nếu có chỉnh sửa Frontend (apps/web)
  npm run build --prefix apps/web
  ```

### Bước 3: Commit và Push lên nhánh của bạn
```bash
git add <cac-file-da-sua>
git commit -m "feat(scope): mo ta ngan gon thay doi"
git push -u origin feat/ten-nhiem-vu
```

### Bước 4: Mở Pull Request (PR) vào `main`
1. Truy cập repo trên GitHub → chọn **Compare & pull request** (base: `main` ← compare: `feat/ten-nhiem-vu`).
2. Điền đầy đủ mô tả PR theo mẫu:
   - **Liên kết Issue:** ghi `Closes #<số-issue>` để GitHub tự đóng Issue khi merge.
   - **Tóm tắt thay đổi:** liệt kê file mới/sửa và quyết định kỹ thuật chính.
   - **Cách kiểm thử:** ghi lệnh đã chạy (`ruff`, `pytest`, `npm run build`) và kết quả.
3. Nếu làm chưa xong nhưng muốn kiểm tra sớm bằng CI, hãy chọn **Create draft pull request**; khi hoàn chỉnh bấm **Ready for review**.
4. Dán link PR vào cột **`Pull Request`** tương ứng trên sheet `DỰ ÁN`.

### Bước 5: Theo dõi CI, xử lý Review & Xung đột (Conflict)
- Chờ 2 job **`build (ubuntu-latest)`** và **`build (windows-latest)`** chuyển xanh. Nếu đỏ, bấm **Details** để xem log lỗi, sửa trên máy rồi `git commit` & `git push` lại lên chính nhánh đó.
- Khi reviewer góp ý: sửa theo góp ý, push commit mới và bấm **Resolve conversation** sau khi đã xử lý.
- **Nếu `main` có code mới gây merge conflict:**
  ```bash
  git fetch origin
  git merge origin/main
  # Mở các file bị đánh dấu <<<<<<< / ======= / >>>>>>> để gộp sạch conflict
  git add <cac-file-da-giai-quyet>
  git commit -m "chore: resolve merge conflicts with main"
  git push
  ```

### Bước 6: Sau khi Merge — Xóa nhánh cũ & Đồng bộ lại `main`
Sau khi PR được merge vào `main`:
1. Bấm **Delete branch** trên trang PR GitHub.
2. Dọn nhánh cục bộ và kéo `main` mới nhất:
   ```bash
   git checkout main
   git pull origin main
   git branch -d feat/ten-nhiem-vu
   ```

---

## 4. Lưu ý riêng về `.gitignore` của dự án

File `.gitignore` hiện dùng cơ chế whitelist (`/*` ở thư mục gốc và chỉ mở ngoại lệ cho `!/src/`, `!/tests/`, `!/docs/`, `!/apps/`, `!/assets/`, `!/scripts/`, `!/packaging/`, `!/.github/`).  
Nếu bạn tạo thư mục mới ngoài các thư mục này ở gốc repo, Git sẽ bỏ qua — hãy trao đổi với Trưởng/Phó ban trước khi thêm thư mục mới ở gốc.
