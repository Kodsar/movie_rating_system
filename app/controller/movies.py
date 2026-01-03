from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.controller.response import success
from app.services.movie_service import get_movies

router = APIRouter(prefix="/api/v1/movies", tags=["movies"])

@router.get(
    "/",
    responses={
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "error": {"code": 422, "message": "Validation error"},
                    }
                }
            },
        }
    },
)
def movies_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    data = get_movies(db, page, page_size)
    return success(data)
