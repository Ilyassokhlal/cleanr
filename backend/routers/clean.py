import json
import base64

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from backend.schemas.options import CleaningRequest
from backend.schemas.responses import CleanResponse
from backend.services import detect, tabular, text
from backend.utils.limiter import limiter
from backend.utils.naming import safe_output_name



# POST /clean — accept an upload, route it to a pipeline, return the cleaned file."""

router = APIRouter()
MAX_AGENT_CHARS = 600_000
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

# Supported output format
MEDIA_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "json": "application/json",
    "txt": "text/plain",
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.post("/clean", response_model=CleanResponse)
@limiter.limit("10/minute") 
async def clean(
    request: Request,
    file: UploadFile = File(...),
    selections: str = Form(...),
    output_format: str = Form(...),
) -> CleanResponse:
    """Clean an uploaded file and hand it back as a download."""
    declared = request.headers.get("content-length")
    if declared and int(declared) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large — the limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large — the limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    try:
        cleaning_request = CleaningRequest(
            selections=json.loads(selections),
            output_format=output_format,
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid options: {exc}") from exc

    if not cleaning_request.selections:
        raise HTTPException(status_code=400, detail="No selections provided")

    try:
        kind = detect.detect_kind(file.filename)
        detect.check_output_format(kind, output_format)
        detect.check_archive_size(data, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if kind == "tabular":
        cleaned_bytes, cleaned_text = await run_in_threadpool(
            tabular.clean, data, file.filename, cleaning_request
        )
    else:
        cleaned_bytes, cleaned_text = await run_in_threadpool(
            text.clean, data, file.filename, cleaning_request
        )

    return CleanResponse(
        filename=safe_output_name(file.filename, output_format),
        media_type=MEDIA_TYPES[output_format],
        content_b64=base64.b64encode(cleaned_bytes).decode("ascii"),
        text=cleaned_text[:MAX_AGENT_CHARS],
    )