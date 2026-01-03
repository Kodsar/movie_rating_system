from fastapi import status
from fastapi.responses import JSONResponse

def success(data, http_status: int = status.HTTP_200_OK):
    return JSONResponse(status_code=http_status, content={"status": "success", "data": data})

def failure(code: int, message: str):
    return JSONResponse(status_code=code, content={"status": "failure", "error": {"code": code, "message": message}})
