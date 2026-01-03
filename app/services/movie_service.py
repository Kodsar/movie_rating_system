from sqlalchemy.orm import Session

from app.repositories.movie_repo import (
    get_director_by_id,
    get_genres_by_ids,
    create_movie,
    insert_movie_genres,
    list_movies_detailed_filtered,
    get_movie_detail,
    get_movie_by_id,
    get_movie_by_id as repo_get_movie_by_id,
    update_movie_fields,
    replace_movie_genres,
    get_director_by_id,
    get_genres_by_ids,
    delete_movie,
    create_movie_rating,
    get_movie_rating_stats,

)

from app.repositories.movie_repo import director_exists, get_genres_by_ids, create_movie, set_movie_genres
from app.core.logging import setup_logger

logger = setup_logger()

def remove_movie(db: Session, movie_id: int) -> bool:
    # Remove movie and its dependencies in a single transaction
    try:
        ok = delete_movie(db, movie_id)
        if not ok:
            return False
        db.commit()
        logger.info("Movie deleted: movie_id=%s", movie_id)

        return True
    except Exception:
        db.rollback()
        raise


def add_movie_rating(db: Session, movie_id: int, score: int):
    

    # Ensure movie exists
    movie = get_movie_by_id(db, movie_id)
    if movie is None:
        raise MovieNotFoundException(movie_id)

    try:
        create_movie_rating(db, movie_id, score)
        db.commit()
        logger.info( "Rating added: movie_id=%s score=%s", movie_id, score,)
    except Exception:
        db.rollback()
        raise

    avg, cnt = get_movie_rating_stats(db, movie_id)

    return {
        "movie_id": movie_id,
        "average_rating": (round(avg, 1) if avg is not None else None),
        "ratings_count": int(cnt),
    }


def update_movie(db: Session, movie_id: int, payload):
    # Validate path param
    if movie_id < 1:
        raise ValueError("Invalid movie_id")

    # Ensure movie exists
    movie = repo_get_movie_by_id(db, movie_id)
    if movie is None:
        raise MovieNotFoundException(movie_id)

    # Validate director
    director = get_director_by_id(db, payload.director_id)
    if director is None:
        raise ValueError("Invalid director_id or genres")

    # Validate genres
    unique_genre_ids = list(dict.fromkeys(payload.genres))
    genres = get_genres_by_ids(db, unique_genre_ids)
    if len(genres) != len(unique_genre_ids):
        raise ValueError("Invalid director_id or genres")

    # Apply changes in a transaction
    try:
        update_movie_fields(
            db=db,
            movie=movie,
            title=payload.title,
            director_id=payload.director_id,
            release_year=payload.release_year,
            cast=payload.cast,
        )
        replace_movie_genres(db, movie.id, unique_genre_ids)

        db.commit()
        db.refresh(movie)
    except Exception:
        db.rollback()
        raise

    return {
        "id": movie.id,
        "title": movie.title,
        "release_year": movie.release_year,
        "director": {"id": director.id, "name": director.name},
        "genres": [g.name for g in genres],
        "cast": movie.cast,
        "average_rating": None,  # Update endpoint typically doesn't recalc here
        "ratings_count": 0,
    }






def add_movie(db: Session, payload):
    # Validate director existence
    director = get_director_by_id(db, payload.director_id)
    if director is None:
        raise ValueError("Invalid director_id or genres")

    # Validate genres existence (all provided IDs must exist)
    unique_genre_ids = list(dict.fromkeys(payload.genres))  # preserve order, remove duplicates
    genres = get_genres_by_ids(db, unique_genre_ids)
    if len(genres) != len(unique_genre_ids):
        raise ValueError("Invalid director_id or genres")



    
    # Create movie + association rows within a transaction
    try:
        movie = create_movie(
            db=db,
            title=payload.title,
            director_id=payload.director_id,
            release_year=payload.release_year,
            cast=payload.cast,
        )
        insert_movie_genres(db, movie.id, unique_genre_ids)

        db.commit()
        logger.info("Movie created: id=%s title='%s'", movie.id, movie.title,)

        db.refresh(movie)
    except Exception:
        db.rollback()
        raise

    

    return {
        "id": movie.id,
        "title": movie.title,
        "release_year": movie.release_year,
        "director": {"id": director.id, "name": director.name},
        "genres": [g.name for g in genres],
        "cast": movie.cast,
        "average_rating": None,
        "ratings_count": 0,
    }








def get_movies(
    db: Session,
    page: int,
    page_size: int,
    title: str | None = None,
    release_year: str | None = None,  # Keep as str to validate manually (custom 422 message)
    genre: str | None = None,
):
    # Basic pagination validation
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("Invalid pagination")

    # Validate release_year (must be an integer if provided)
    ry_int: int | None = None
    if release_year is not None:
        if not release_year.strip().isdigit():
            raise ValueError("Invalid release_year")
        ry_int = int(release_year)

    total_items, movies_pack, genres_map = list_movies_detailed_filtered(
        db=db,
        page=page,
        page_size=page_size,
        title=title,
        release_year=ry_int,
        genre=genre,
    )

    # Build response items
    items = []
    for pack in movies_pack:
        m = pack["movie"]
        d = pack["director"]

        avg = pack["avg_rating"]
        cnt = pack["ratings_count"] or 0

        items.append(
            {
                "id": m.id,
                "title": m.title,
                "release_year": m.release_year,
                "director": {
                    "id": d.id,
                    "name": d.name,
                },
                "genres": genres_map.get(m.id, []),
                "average_rating": (round(float(avg), 1) if avg is not None else None),
                "ratings_count": int(cnt),
            }
        )

    return {
        "page": page,
        "page_size": page_size,
        "total_items": int(total_items),
        "items": items,
    }


def get_movie_by_id(db: Session, movie_id: int):
    # Basic validation for path parameter
    if movie_id < 1:
        raise ValueError("Invalid movie_id")

    pack = get_movie_detail(db, movie_id)
    if pack is None:
        return None

    m = pack["movie"]
    d = pack["director"]

    avg = pack["avg_rating"]
    cnt = pack["ratings_count"] or 0

    return {
        "id": m.id,
        "title": m.title,
        "release_year": m.release_year,
        "director": {
            "id": d.id,
            "name": d.name,
            "birth_year": d.birth_year,
            "description": d.description,
        },
        "genres": pack["genres"],
        "cast": m.cast,
        "average_rating": (round(float(avg), 1) if avg is not None else None),
        "ratings_count": int(cnt),
    }
