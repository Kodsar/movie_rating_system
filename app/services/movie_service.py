from sqlalchemy.orm import Session

from app.repositories.movie_repo import (
    list_movies_detailed_filtered,
    get_movie_detail,
)

from app.repositories.movie_repo import director_exists, get_genres_by_ids, create_movie, set_movie_genres


def add_movie(db: Session, payload):
    # Validate director existence
    if not director_exists(db, payload.title and payload.director_id):
        raise ValueError("Invalid director_id or genres")

    # Validate genres existence
    genres = get_genres_by_ids(db, payload.genres)
    if len(genres) != len(set(payload.genres)):
        raise ValueError("Invalid director_id or genres")

    # Create movie + association rows in a transaction
    movie = create_movie(db, payload.title, payload.director_id, payload.release_year, payload.cast)
    set_movie_genres(db, movie.id, payload.genres)

    db.commit()
    db.refresh(movie)

    return {
        "id": movie.id,
        "title": movie.title,
        "release_year": movie.release_year,
        "director": {"id": payload.director_id, "name": movie.director.name},
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
