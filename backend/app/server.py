"""Start the API server using settings from backend/.env."""

import uvicorn

from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        ssl_certfile=str(settings.tls_cert_path) if settings.tls_cert_path else None,
        ssl_keyfile=str(settings.tls_key_path) if settings.tls_key_path else None,
    )