from fastapi import FastAPI

from backend.services.detect import EXTENSIONS
from backend.config import OUTPUT_FORMATS, TABULAR_OPTIONS, TEXT_OPTIONS
from backend.schemas.options import OptionsResponse
from backend.routers import clean
from backend.routers import ask

from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# Cleanr API — app setup and routes.

app = FastAPI(title="Cleanr API")


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