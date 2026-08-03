from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.services.detect import EXTENSIONS
from backend.config import OUTPUT_FORMATS, TABULAR_OPTIONS, TEXT_OPTIONS
from backend.schemas.options import OptionsResponse
from backend.routers import clean
from backend.routers import ask
from backend.errors import CleanrError

from dotenv import load_dotenv

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.utils.limiter import limiter

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv() # Load environment variables from .env file

# Cleanr API — app setup and routes.

app = FastAPI(title="Cleanr API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
def root() -> dict[str, str]:
    """Landing response so the bare URL isn't a 404."""
    return {
        "service": "Cleanr API",
        "status": "running",
        "docs": "/docs",
        "endpoints": "/options, /clean, /ask, /health",
    }

@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check — also what you hit to confirm uvicorn came up."""
    return {"status": "ok"}

@app.get("/options", response_model=OptionsResponse)
def get_options() -> OptionsResponse:
    """Serve the form definition the frontend renders from."""
    return OptionsResponse(
        tabular=TABULAR_OPTIONS,
        text=TEXT_OPTIONS,
        output_formats=OUTPUT_FORMATS,
        extensions=EXTENSIONS,
    )


# Including the routers for the /clean and /ask endpoints.
app.include_router(clean.router)
app.include_router(ask.router)


# Exception handlers for the CleanrError hierarchy and any other unhandled exceptions.
@app.exception_handler(CleanrError)
async def handle_cleanr_error(request: Request, exc: CleanrError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong processing that file."})