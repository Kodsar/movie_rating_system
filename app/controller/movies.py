from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.controller.response import success, failure
from app.services.movie_service import get_movies, get_movie_by_id, add_movie
from app.schemas.movie import MovieCreate
from app.services.movie_service import add_movie


router = APIRouter(prefix="/api/v1/movies", tags=["movies"])




@router.post("/", status_code=status.HTTP_201_CREATED)
def create_movie_endpoint(payload: MovieCreate, db: Session = Depends(get_db)):
    try:
        data = add_movie(db, payload)
        return success(data, http_status=status.HTTP_201_CREATED)
    except ValueError as e:
        return failure(422, str(e) if str(e) else "Invalid director_id or genres")




@router.get(
    "/",
    responses={
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "error": {"code": 422, "message": "Invalid input"},
                    }
                }
            },
        }
    },
)
def movies_list(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
    title: str | None = Query(None, description="Partial title match (case-insensitive)"),
    release_year: str | None = Query(None, description="Release year (must be an integer)"),
    genre: str | None = Query(None, description="Exact genre name match"),
    db: Session = Depends(get_db),
):
    try:
        data = get_movies(
            db=db,
            page=page,
            page_size=page_size,
            title=title,
            release_year=release_year,
            genre=genre,
        )
        return success(data, http_status=status.HTTP_200_OK)
    except ValueError as e:
        msg = str(e) if str(e) else "Invalid input"
        return failure(422, msg)


@router.get(
    "/{movie_id}",
    responses={
        404: {
            "description": "Movie Not Found",
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "error": {"code": 404, "message": "Movie not found"},
                    }
                }
            },
        }
    },
)
def movie_detail(
    movie_id: int = Path(..., ge=1, description="Movie ID (path parameter)"),
    db: Session = Depends(get_db),
):
    try:
        data = get_movie_by_id(db=db, movie_id=movie_id)
    except ValueError:
        return failure(422, "Invalid movie_id")

    if data is None:
        return failure(404, "Movie not found")

    return success(data, http_status=status.HTTP_200_OK)
