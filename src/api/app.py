from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from src.core.settings import get_settings
from src.core.storage import export_file_for_date, latest_export_file
from src.spiders.registry import SITE_ORDER


def create_app() -> FastAPI:
    app = FastAPI(title="Drama Web Crawler", version="0.1.0")

    @app.get("/api/v1/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/exports/{site}")
    def download_export(
        site: str,
        export_date: date | None = Query(default=None, alias="date"),
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
