"""Data export: CSV (zipped, one file per module) and JSON.

Behind the Green PIN gate because the export includes income and investment
figures - the same confidentiality boundary that protects those numbers
everywhere else in the app.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

from fastapi import APIRouter, Response

from app.core.deps import DbSession, UnlockedAuth
from app.models.enums import AuditAction
from app.services import audit, export as service

router = APIRouter(prefix="/export", tags=["Data Export"])


@router.get("/json")
def export_json(db: DbSession, ctx: UnlockedAuth) -> Response:
    data = service.collect_user_data(db, ctx.user_id)
    audit.record(
        db, user_id=ctx.user_id, action=AuditAction.EXPORT.value, entity_type="user",
        entity_id=ctx.user_id, summary="Exported data as JSON",
    )
    db.commit()
    filename = f"bahi-khata-export-{date.today().isoformat()}.json"
    return Response(
        content=service.to_json(data),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv")
def export_csv(db: DbSession, ctx: UnlockedAuth) -> Response:
    data = service.collect_user_data(db, ctx.user_id)
    parts = service.to_csv_zip_parts(data)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)

    audit.record(
        db, user_id=ctx.user_id, action=AuditAction.EXPORT.value, entity_type="user",
        entity_id=ctx.user_id, summary="Exported data as CSV",
    )
    db.commit()

    filename = f"bahi-khata-export-{date.today().isoformat()}.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
