from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.controller.response import success, failure
from app.schemas.movie import MovieCreate, MovieUpdate, MovieRatingCreate
from app.services.movie_service import (
    get_movies,
    get_movie_detail_by_id,
    add_movie,
    update_movie,
    remove_movie,
    add_movie_rating,
)

router = APIRouter(prefix="/api/v1/movies", tags=["movies"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "error": {"code": 422, "message": "Invalid director_id or genres"},
                    }
                }
            },
        }
    },
)
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
        data = get_movie_detail_by_id(db=db, movie_id=movie_id)
    except ValueError:
        return failure(422, "Invalid movie_id")

    if data is None:
        return failure(404, "Movie not found")

    return success(data, http_status=status.HTTP_200_OK)


@router.put(
    "/{movie_id}",
    responses={
        404: {
            "description": "Movie Not Found",
            "content": {"application/json": {"example": {"status": "failure", "error": {"code": 404, "message": "Movie not found"}}}},
        },
        422: {
            "description": "Validation Error",
            "content": {"application/json": {"example": {"status": "failure", "error": {"code": 422, "message": "Invalid director_id or genres"}}}},
        },
    },
)
def update_movie_endpoint(
    movie_id: int = Path(..., ge=1),
    payload: MovieUpdate = ...,
    db: Session = Depends(get_db),
):
    try:
        data = update_movie(db=db, movie_id=movie_id, payload=payload)
    except ValueError as e:
        msg = str(e) if str(e) else "Invalid input"
        return failure(422, msg)

    if data is None:
        return failure(404, "Movie not found")

    return success(data, http_status=status.HTTP_200_OK)


@router.delete("/{movie_id}", status_code=status.HTTP_200_OK)
def delete_movie_endpoint(
    movie_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    ok = remove_movie(db, movie_id)
    if not ok:
        return failure(404, "Movie not found")
    return success({"message": "Movie deleted"})


@router.post(
    "/{movie_id}/ratings",
    status_code=status.HTTP_201_CREATED,
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
        },
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "status": "failure",
                        "error": {"code": 422, "message": "Score must be an integer between 1 and 10"},
                    }
                }
            },
        },
    },
)
def create_rating_endpoint(
    movie_id: int = Path(..., ge=1),
    payload: MovieRatingCreate = ...,
    db: Session = Depends(get_db),
):
    try:
        data = add_movie_rating(db=db, movie_id=movie_id, score=payload.score)
    except ValueError as e:
        msg = str(e) if str(e) else "Score must be an integer between 1 and 10"
        return failure(422, msg)

    if data is None:
        return failure(404, "Movie not found")

    return success(data, http_status=status.HTTP_201_CREATED)
