from fastapi import FastAPI, HTTPException, Request
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from app.api import auth, inference, models, outputs, system
from app.config import settings
from app.services import auth_service, data_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Model Khôi Phục Chữ Viết",
    description="Công cụ chạy model khôi phục chữ viết trong ảnh trên máy tính cá nhân.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    response = None
    if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        same_origin = f"{request.url.scheme}://{request.url.netloc}"
        if origin not in settings.cors_origins and origin != same_origin:
            response = JSONResponse(
                status_code=403,
                content={"detail": "A valid Origin header is required for this request."},
            )

    if response is None:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.include_router(auth.router)
app.include_router(models.router)
app.include_router(inference.router)
app.include_router(outputs.router)
app.include_router(system.router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    # Ensure storage directories exist
    settings.models_path
    settings.uploads_path
    settings.outputs_path
    auth_service.initialize()
    data_service.initialize()
    logger.info("Model Khôi Phục Chữ Viết backend started.")
# Phục vụ giao diện đã build (frontend/dist). Nếu chưa build thì bỏ qua, chế độ dev vẫn chạy bình thường.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        requested = (FRONTEND_DIST / full_path).resolve()
        if full_path and requested.is_file() and FRONTEND_DIST.resolve() in requested.parents:
            return FileResponse(requested)
        return FileResponse(FRONTEND_DIST / "index.html")