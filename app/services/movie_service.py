from sqlalchemy.orm import Session
from app.repositories.movie_repo import list_movies_detailed


def get_movies(
    db: Session,
    page: int,
    page_size: int,
    title: str | None = None,
    release_year: int | None = None,
    genre: str | None = None,
):
    # Basic pagination validation
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("Invalid pagination")

    total_items, movies_pack, genres_map = list_movies_detailed(
        db,
        page,
        page_size,
        title=title,
        release_year=release_year,
        genre=genre,
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
