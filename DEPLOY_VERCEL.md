# Deploy frontend tren Vercel

## Mo hinh

- Vercel host frontend React/Vite va tu cap HTTPS.
- Backend FastAPI va MySQL chay tren cac dich vu rieng.
- Vercel rewrite `/api/*` den backend bang HTTPS, giu API cung origin voi frontend de cookie dang nhap hoat dong.
- Hinh/model/ket qua van duoc ghi vao thu muc backend. Can persistent disk co encryption-at-rest; filesystem tam cua serverless khong duoc xem la noi luu tru lau dai.

## Vercel

1. Import repository len Vercel, dat **Root Directory** la `frontend`.
2. Build command: `npm run build`; output directory: `dist`.
3. Sau khi tao backend va co hostname HTTPS, sua `frontend/vercel.json`: thay `your-backend-domain.example` bang hostname backend that, khong them `/` cuoi hostname. Giu prefix `/api` trong destination.
4. Deploy lai frontend. `/api/health` tren domain Vercel phai tra ve `{"status":"ok"}`.

Vercel cung cap HTTPS cho domain frontend. Rewrite phai tro den URL `https://` cua backend; khong dung HTTP.

## Backend

Dat cac bien moi truong tu `backend/.env.example` trong dashboard cua nha cung cap backend:

- `APP_HOST=0.0.0.0`, `APP_PORT` theo cong ma nha cung cap yeu cau.
- `TLS_TERMINATED_BY_PROXY=true` va `SESSION_COOKIE_SECURE=true` neu nha cung cap ket thuc HTTPS tai reverse proxy. Chi bat tuy chon nay khi hostname backend cong khai chi truy cap qua HTTPS.
- De cookie cung origin hoat dong, dat `FRONTEND_ORIGIN` bang origin Vercel, vi du `https://ten-du-an.vercel.app` (khong co `/` cuoi). `CORS_ALLOWED_ORIGINS` co the de trong neu khong co frontend origin phu.
- Dat `SESSION_COOKIE_SAMESITE=lax`.
- Dat thong tin MySQL bang thong tin cua dich vu MySQL; dung CA do nha cung cap cap trong `MYSQL_SSL_CA` de bat TLS va xac minh danh tinh may chu. Khong bo qua xac minh chung chi.
- Tao cac thu muc `MODELS_DIR`, `UPLOADS_DIR`, va `OUTPUTS_DIR` tren persistent disk duoc mount. Dam bao tai khoan chay backend co quyen doc/ghi.
- Dung mot persistent disk/database co **encryption at rest** duoc nha cung cap xac nhan. HTTPS va TLS MySQL chi ma hoa du lieu khi truyen; repo khong tu ma hoa cac file model/hinh tren dia.

Neu dung Vercel preview deployment, moi preview co origin khac production. Them origin preview can thiet vao `CORS_ALLOWED_ORIGINS` hoac dung deployment production; khong dat wildcard cho cookie credentials.

## Gioi han can tinh

- Backend can chay PyTorch va inference, nen free/serverless runtime co the khong du RAM/CPU, gioi han thoi gian chay, hoac khong co persistent disk. Kiem tra gioi han upload va thoi gian request cua ca Vercel/backend truoc khi dua len production.
- Database phai la MySQL/MariaDB. PostgreSQL khong tuong thich voi cac truy van PyMySQL hien tai.
- Khong commit `backend/.env`, mat khau database, private key TLS, hay credential provider vao Git.
