from sqlalchemy.orm import Session

from app.core.logging import setup_logger
from app.repositories.movie_repo import (
    get_director_by_id,
    get_genres_by_ids,
    create_movie,
    insert_movie_genres,
    list_movies_detailed_filtered,
    get_movie_detail,
    get_movie_by_id as repo_get_movie_by_id,
    update_movie_fields,
    replace_movie_genres,
    delete_movie,
    create_movie_rating,
)

logger = setup_logger()


def add_movie(db: Session, payload):
    logger.info(
        "add_movie called: title='%s' director_id=%s release_year=%s genres=%s",
        getattr(payload, "title", None),
        getattr(payload, "director_id", None),
        getattr(payload, "release_year", None),
        getattr(payload, "genres", None),
    )

    director = get_director_by_id(db, payload.director_id)
    if director is None:
        logger.warning("add_movie invalid director_id=%s", payload.director_id)
        raise ValueError("Invalid director_id or genres")

    unique_genre_ids = list(dict.fromkeys(payload.genres))
    genres = get_genres_by_ids(db, unique_genre_ids)
    if len(genres) != len(unique_genre_ids):
        logger.warning(
            "add_movie invalid genres: requested=%s found=%s",
            unique_genre_ids,
            [g.id for g in genres],
        )
        raise ValueError("Invalid director_id or genres")

    try:
        movie = create_movie(
            db=db,
            title=payload.title,
            director_id=payload.director_id,
            release_year=payload.release_year,
            cast=payload.cast,
        )
        logger.info("Movie row created (not committed yet): movie_id=%s", movie.id)

        insert_movie_genres(db, movie.id, unique_genre_ids)
        logger.info("Movie genres inserted: movie_id=%s genre_ids=%s", movie.id, unique_genre_ids)

        db.commit()
        db.refresh(movie)
        logger.info("Movie created: id=%s title='%s'", movie.id, movie.title)

    except Exception:
        db.rollback()
        logger.exception(
            "add_movie failed -> rollback: title='%s' director_id=%s",
            getattr(payload, "title", None),
            getattr(payload, "director_id", None),
        )
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


def update_movie(db: Session, movie_id: int, payload):
    logger.info(
        "update_movie called: movie_id=%s title='%s' director_id=%s release_year=%s genres=%s",
        movie_id,
        getattr(payload, "title", None),
        getattr(payload, "director_id", None),
        getattr(payload, "release_year", None),
        getattr(payload, "genres", None),
    )

    if movie_id < 1:
        logger.warning("update_movie invalid movie_id=%s", movie_id)
        raise ValueError("Invalid movie_id")

    movie = repo_get_movie_by_id(db, movie_id)
    if movie is None:
        logger.info("update_movie movie not found: movie_id=%s", movie_id)
        return None

    director = get_director_by_id(db, payload.director_id)
    if director is None:
        logger.warning(
            "update_movie invalid director_id=%s for movie_id=%s",
            payload.director_id,
            movie_id,
        )
        raise ValueError("Invalid director_id or genres")

    unique_genre_ids = list(dict.fromkeys(payload.genres))
    genres = get_genres_by_ids(db, unique_genre_ids)
    if len(genres) != len(unique_genre_ids):
        logger.warning(
            "update_movie invalid genres for movie_id=%s: requested=%s found=%s",
            movie_id,
            unique_genre_ids,
            [g.id for g in genres],
        )
        raise ValueError("Invalid director_id or genres")

    try:
        update_movie_fields(
            db=db,
            movie=movie,
            title=payload.title,
            director_id=payload.director_id,
            release_year=payload.release_year,
            cast=payload.cast,
        )
        logger.info("Movie fields updated (not committed yet): movie_id=%s", movie_id)

        replace_movie_genres(db, movie.id, unique_genre_ids)
        logger.info("Movie genres replaced: movie_id=%s genre_ids=%s", movie_id, unique_genre_ids)

        db.commit()
        db.refresh(movie)
        logger.info("Movie updated: id=%s title='%s'", movie.id, movie.title)

    except Exception:
        db.rollback()
        logger.exception("update_movie failed -> rollback: movie_id=%s", movie_id)
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


def remove_movie(db: Session, movie_id: int) -> bool:
    logger.info("remove_movie called: movie_id=%s", movie_id)

    if movie_id < 1:
        logger.warning("remove_movie invalid movie_id=%s", movie_id)
        raise ValueError("Invalid movie_id")

    try:
        ok = delete_movie(db, movie_id)
        if not ok:
            logger.info("remove_movie movie not found: movie_id=%s", movie_id)
            return False

        db.commit()
        logger.info("Movie deleted: movie_id=%s", movie_id)
        return True

    except Exception:
        db.rollback()
        logger.exception("remove_movie failed -> rollback: movie_id=%s", movie_id)
        raise


def add_movie_rating(db: Session, movie_id: int, score: int):
    logger.info("add_movie_rating called: movie_id=%s score=%s", movie_id, score)

    if movie_id < 1:
        logger.warning("add_movie_rating invalid movie_id=%s", movie_id)
        raise ValueError("Invalid movie_id")

    if not isinstance(score, int) or score < 1 or score > 10:
        logger.warning("add_movie_rating invalid score=%s for movie_id=%s", score, movie_id)
        raise ValueError("Score must be an integer between 1 and 10")

    movie = repo_get_movie_by_id(db, movie_id)
    if movie is None:
        logger.info("add_movie_rating movie not found: movie_id=%s", movie_id)
        return None

    try:
        rating = create_movie_rating(db, movie_id, score)
        db.commit()
        db.refresh(rating)
        logger.info(
            "Rating added: movie_id=%s score=%s rating_id=%s",
            movie_id,
            score,
            rating.id,
        )

    except Exception:
        db.rollback()
        logger.exception(
            "add_movie_rating failed -> rollback: movie_id=%s score=%s",
            movie_id,
            score,
        )
        raise

    created_at = None
    if hasattr(rating, "rated_at") and rating.rated_at is not None:
        created_at = rating.rated_at
    elif hasattr(rating, "created_at") and rating.created_at is not None:
        created_at = rating.created_at

    created_at_str = created_at.isoformat() if created_at is not None else None

    return {
        "rating_id": rating.id,
        "movie_id": rating.movie_id,
        "score": rating.score,
        "created_at": created_at_str,
    }


def get_movies(
    db: Session,
    page: int,
    page_size: int,
    title: str | None = None,
    release_year: str | None = None,
    genre: str | None = None,
):
    logger.info(
        "get_movies called: page=%s page_size=%s title=%s release_year=%s genre=%s",
        page,
        page_size,
        title,
        release_year,
        genre,
    )

    if page < 1 or page_size < 1 or page_size > 100:
        logger.warning("get_movies invalid pagination: page=%s page_size=%s", page, page_size)
        raise ValueError("Invalid pagination")

    ry_int: int | None = None
    if release_year is not None:
        if not release_year.strip().isdigit():
            logger.warning("get_movies invalid release_year='%s'", release_year)
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

    logger.info(
        "get_movies result: total_items=%s returned=%s page=%s page_size=%s",
        int(total_items),
        len(movies_pack),
        page,
        page_size,
    )

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
                "director": {"id": d.id, "name": d.name},
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


def get_movie_detail_by_id(db: Session, movie_id: int):
    logger.info("get_movie_detail_by_id called: movie_id=%s", movie_id)

    if movie_id < 1:
        logger.warning("get_movie_detail_by_id invalid movie_id=%s", movie_id)
        raise ValueError("Invalid movie_id")

    pack = get_movie_detail(db, movie_id)
    if pack is None:
        logger.info("get_movie_detail_by_id not found: movie_id=%s", movie_id)
        return None

    m = pack["movie"]
    d = pack["director"]

    avg = pack["avg_rating"]
    cnt = pack["ratings_count"] or 0

    logger.info(
        "get_movie_detail_by_id result: movie_id=%s title='%s' avg=%s cnt=%s",
        m.id,
        m.title,
        avg,
        int(cnt),
    )

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
