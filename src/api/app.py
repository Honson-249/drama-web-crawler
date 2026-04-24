from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader

from src.core.settings import get_settings
from src.core.storage import export_file_for_date, latest_export_file
from src.spiders.registry import SITE_ORDER


API_KEY = "kL9pQ2rS4tU6vW8xY0zA1bC3dE5fG7h"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    return api_key


def create_app() -> FastAPI:
    app = FastAPI(title="Drama Web Crawler", version="0.1.0")

    @app.get("/api/v1/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/exports/{site}")
    def download_export(
        site: str,
        export_date: date | None = Query(default=None, alias="date"),
        _api_key: str = Depends(verify_api_key),
    ) -> FileResponse:
        normalized_site = site.lower()
        if normalized_site not in SITE_ORDER:
            raise HTTPException(status_code=404, detail=f"unknown site: {site}")

        settings = get_settings()
        target = (
            export_file_for_date(settings, normalized_site, export_date)
            if export_date
            else latest_export_file(settings, normalized_site)
        )
        if target is None:
            raise HTTPException(status_code=404, detail="csv export not found")

        return FileResponse(
            target,
            media_type="text/csv",
            filename=target.name,
        )

    return app


app = create_app()
