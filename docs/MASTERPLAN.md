# Neuro Studio — Kế hoạch tổng thể dự án (Masterplan)

> **Dự án:** Neuro Studio — LAILA AI Project (`maithedung79/NeuroStudio-LAILA`)  
> **Phiên bản hiện tại:** `0.0.1b1` (Beta)  
> **Đơn vị thực hiện:** Ban Chuyên Môn — Câu lạc bộ AI Lê Quý Đôn (LAILA)  
> **Cập nhật:** 26/11/2026

---

## 1. Khảo sát hiện trạng Neuro Studio (`0.0.1b1`)

Neuro Studio hiện là một **ứng dụng Machine Learning trực quan chạy cục bộ cho một người dùng (single-user, local-first)**, kết hợp giao diện React trên trình duyệt với tầng thực thi Python thực (`scikit-learn`, `PyTorch`, `transformers`, `umap-learn`).

### 1.1. Các chức năng đã có
| Phân hệ | Thành phần mã nguồn chính | Khả năng hiện tại |
|---|---|---|
| **Visual Studio (5 Labs)** | `src/neurostudio/core/`, `compiler.py`, `engine/layers.py`, `engine/portable.py` | Kéo-thả `DataGraph`, `ModelGraph`, `ExperimentGraph`; 8 classifier + 8 regressor (`sklearn`), 100+ khối tensor PyTorch; chống rò rỉ dữ liệu (`Split` trước `Imputer`/`Scaler`/`OneHotEncoder`/`PCA`, kiểm tra trùng lặp chéo tập); sinh code và xuất dự án Python độc lập. |
| **Task Studio** | `advanced_schema.py`, `engine/tasks.py`, `task_datasets.py`, `task_export.py` | 8 bài toán có giám sát: Image Classification (15 backbone torchvision), Segmentation (U-Net), Detection (Faster R-CNN), Image Reconstruction (Autoencoder/VAE), Text Classification (BiGRU/Transformer/BERT/LoRA), Text Generation, Audio Classification, Time-Series Forecasting. |
| **Exploration Studio** | `exploration_schema.py`, `engine/exploration.py`, `exploration_export.py` | Phân cụm KMeans/DBSCAN/Agglomerative + giảm chiều PCA/t-SNE/UMAP và xuất pipeline độc lập. |
| **LAILA Academy** | `curriculum.json`, `apps/web/src/LearningStudio.tsx` | 12 bài học song ngữ Việt/Anh gắn nguồn học liệu mở và bài kiểm tra quiz lưu tiến độ. |
| **Vận hành & Bảo toàn** | `launcher.py`, `supervisor.py`, `worker.py`, `setup.py`, `backup.py`, `offline.py` | Tách biệt API server (không import `torch`/`sklearn`) với ML worker subprocess; cài môi trường side-by-side qua `uv` + `--require-hashes`; backup/restore workspace và tạo gói cài offline. |

### 1.2. Các hạn chế hiện tại khi hướng tới môi trường nhiều người dùng (Multi-user)
1. **Chưa có định danh tài khoản & xác thực người dùng:** `src/neurostudio/api.py` hiện chỉ cấp một token phiên ngẫu nhiên toàn cục (`neuro_session` cookie + header `X-NeuroStudio`) dùng chung cho mọi request trên máy cục bộ và khóa cứng `Host` ở loopback (`127.0.0.1`, `localhost`, `::1`).
2. **Chưa có sở hữu & cách ly dữ liệu:** Các bảng `projects`, `archived_projects`, `jobs`, `datasets`, `progress` trong `studio.db` (`src/neurostudio/storage.py`) chưa có trường `owner_id`; mọi client đều thấy và chỉnh sửa được toàn bộ dữ liệu chung.
3. **Worker chạy trực tiếp trên máy chủ (chưa sandbox):** `Supervisor` (`src/neurostudio/supervisor.py`) chạy tuần tự một job tại một thời điểm bằng quyền hệ điều hành hiện tại; các tính năng custom metric/loss (`exec()` trong `src/neurostudio/engine/objectives.py`) và `joblib.load` không an toàn nếu mở cho nhiều người dùng bên ngoài mà chưa cách ly container.
4. **Nợ kỹ thuật giao diện & kiểm thử:** Giao diện React tập trung lớn trong `apps/web/src/main.tsx` (~74 KB) với `type Any = any`; trước Tuần 1 chưa có thư mục `tests/` (đã bổ sung bộ 16 test `pytest` + `ruff` + CI trong Tuần 1).

---

## 2. Mục tiêu giai đoạn hiện tại (Đợt 1: 5 tuần, 27/11 – 31/12/2026)

Chuyển đổi nền tảng lõi của Neuro Studio từ **chế độ không có tài khoản** sang **kiến trúc hỗ trợ tài khoản, xác thực phiên và cách ly dữ liệu theo chủ sở hữu**, đồng thời chuẩn bị đề xuất kỹ thuật (RFC) cho cách ly worker huấn luyện bằng Docker ở giai đoạn sau.

### Phạm vi TRONG đợt 1 (In-scope)
- Thiết lập CI/CD chuẩn hóa (`ruff`, `pytest`, build Frontend, build wheel, branch protection trên `main`) và bộ tài liệu nền tảng (`docs/`).
- Hệ thống tài khoản: CSDL người dùng (mật khẩu băm an toàn), dịch vụ xác thực & quản lý phiên/token, API đăng ký / đăng nhập / đăng xuất / lấy thông tin phiên (`/api/v1/auth/*`).
- Giao diện React đăng ký, đăng nhập, quản lý trạng thái phiên và bảo vệ điều hướng trang.
- Mở rộng CSDL & tầng phân quyền sở hữu tài nguyên (ưu tiên `projects` và mở rộng dần sang `datasets`/`jobs` theo thiết kế), áp dụng cho cả nhóm API đọc (`read_routes`) và API ghi (`write_routes`).
- Nghiên cứu và lập đề xuất kiến trúc cách ly training worker bằng Docker (`docs/DOCKER_WORKER_RFC.md`).
- Bộ kiểm thử tích hợp xác thực & cách ly dữ liệu end-to-end giữa nhiều tài khoản.

### Phạm vi NGOÀI đợt 1 (Out-of-scope — để dành Giai đoạn 2)
- Chưa mở chạy mã Python tùy chỉnh (`metric_code`/`loss_code`) từ người dùng công khai trên Internet; chưa triển khai cụm Docker worker production.
- Chưa thêm OAuth bên thứ ba (Google/GitHub login), quên mật khẩu qua email hay phân quyền vai trò phức tạp (RBAC tổ chức).
- Chưa thay đổi logic lõi huấn luyện ML trong `src/neurostudio/engine/`.

---

## 3. Lộ trình triển khai 5 tuần (27/11 – 31/12/2026)

> **Nguyên tắc phối hợp:** Mọi module trong cùng một tuần được chia tách độc lập qua **hợp đồng giao diện** (xem `docs/API.md` và `docs/ARCHITECTURE.md`) và kiểm thử bằng `mock/fake` để không ai phải chờ người khác hoàn thành mới bắt đầu code.

| Tuần | Mốc thời gian | Trọng tâm kỹ thuật | Module / Đầu việc độc lập | Thời điểm tích hợp |
|---|---|---|---|---|
| **T1** | 27/11 – 03/12 | **Nền tảng & CI** *(Hoàn thành sớm)* | CI (`ruff`, `pytest`, Frontend build, Branch Protection); bộ 5 tài liệu `docs/`; danh sách GitHub Issues. | Đã hoàn tất trên `main` trước khi mở T2. |
| **T2** | 04/12 – 10/12 | **Lõi xác thực Backend (Song song)** | 1. API Router đăng ký/đăng nhập (mock repo/service)<br>2. CSDL tài khoản (`users` schema, migration, repository)<br>3. Dịch vụ xác thực (hash password, token/session, middleware)<br>4. Khung contract test & rà soát đồng bộ giao diện | Ghép 3 module Backend thật ở **T3**. |
| **T3** | 11/12 – 17/12 | **Tích hợp Auth Backend + UI Auth + Docker RFC** | 1. Tích hợp router + repo + auth service thành API chạy thật<br>2. Dựng 2 trang React Đăng nhập / Đăng ký (API giả lập)<br>3. Nghiên cứu cách ly worker huấn luyện bằng Docker (`docs/DOCKER_WORKER_RFC.md`) | Kết nối UI với API thật ở **T4**. |
| **T4** | 18/12 – 24/12 | **Nối UI Auth + Schema & Logic Ownership** | 1. Kết nối giao diện React với API Auth thật + quản lý phiên & bảo vệ route<br>2. Bổ sung thông tin sở hữu tài nguyên trong `studio.db` + migration bảo toàn dữ liệu cũ<br>3. Xây dựng cơ chế/dependency kiểm tra quyền sở hữu tài nguyên (test giả lập) | Áp dụng ownership vào toàn bộ API ở **T5**. |
| **T5** | 25/12 – 31/12 | **Phân quyền API Đọc/Ghi + Kiểm thử E2E** | 1. Phân quyền API tạo/sửa/xóa (`write_routes`, hạn 28/12)<br>2. Phân quyền API đọc/liệt kê (`read_routes` + đăng ký router chính, hạn 29/12)<br>3. Kiểm thử tích hợp E2E xác thực & cách ly dữ liệu chéo tài khoản (30/12) & chốt merge (31/12) | Chốt tích hợp đợt 1 vào **31/12/2026**. |

---

## 4. Định hướng Giai đoạn 2 (sau 31/12/2026)

1. **Cách ly thực thi huấn luyện (Containerized Workers):** Hiện thực hóa đề xuất từ `docs/DOCKER_WORKER_RFC.md` (giới hạn CPU/RAM/GPU, không chia sẻ thư mục giữa các tài khoản, tắt hoặc sandbox custom code).
2. **Hàng đợi đa người dùng:** Mở rộng `Supervisor` để hỗ trợ giới hạn quota job theo từng tài khoản thay vì một hàng đợi dùng chung duy nhất.
3. **Tái cấu trúc Frontend:** Tách `apps/web/src/main.tsx` thành các module theo trang/feature và thay thế `type Any = any` bằng kiểu TypeScript đầy đủ.
4. **Mở rộng Visual ModelGraph:** Hỗ trợ đầu vào 1D/chuỗi cho các lớp `Conv1D`, `RNN`/`GRU`/`LSTM`, `TransformerEncoderLayer` vốn đã tồn tại trong `engine/layers.py`.

---

## 5. Tài liệu liên quan

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — Kiến trúc hệ thống hiện tại và thiết kế tài khoản, phân quyền, cách ly dữ liệu.
- [docs/API.md](API.md) — Đặc tả API xác thực và hợp đồng giao diện Python giữa các module T2–T5.
- [docs/SETUP.md](SETUP.md) — Hướng dẫn cài đặt môi trường và chạy kiểm thử cục bộ.
- [docs/CONTRIBUTING.md](CONTRIBUTING.md) — Quy trình Git/GitHub, tiêu chuẩn PR và quy tắc review.
