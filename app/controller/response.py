from fastapi import status
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse


def success(data, http_status: int = 200):
    return JSONResponse(
        status_code=http_status,
        content=jsonable_encoder({"status": "success", "data": data}),
    )


def failure(code: int, message: str, http_status: int | None = None):
    status_code = http_status if http_status is not None else code
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {"status": "failure", "error": {"code": code, "message": message}}
        ),
    )
