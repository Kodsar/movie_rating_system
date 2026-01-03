from fastapi import FastAPI, Request

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.controller.movies import router as movies_router

from app.middleware.logging import RequestLoggingMiddleware
from app.core.logging import setup_logger
logger = setup_logger()

app = FastAPI(title="Movie Rating System")

app.add_middleware(RequestLoggingMiddleware)

@app.get("/health")
def health():
    return {"ok": True}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status": "failure", "error": {"code": 422, "message": "Validation error"}},
    )

app.include_router(movies_router)
logger.info("Application startup complete")
