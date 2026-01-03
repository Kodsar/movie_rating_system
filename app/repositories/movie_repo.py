from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Movie, Director, Genre, MovieRating
from app.models.movie_genre import genres_movie






def director_exists(db: Session, director_id: int) -> bool:
    return db.execute(select(Director.id).where(Director.id == director_id)).first() is not None


def get_genres_by_ids(db: Session, genre_ids: list[int]) -> list[Genre]:
    if not genre_ids:
        return []
    return db.execute(select(Genre).where(Genre.id.in_(genre_ids))).scalars().all()


def create_movie(db: Session, title: str, director_id: int, release_year: int, cast: str | None):
    movie = Movie(title=title, director_id=director_id, release_year=release_year, cast=cast)
    db.add(movie)
    db.flush()  # Get movie.id without committing yet
    return movie


def set_movie_genres(db: Session, movie_id: int, genre_ids: list[int]):
    # Insert rows into association table
    if not genre_ids:
        return
    db.execute(
        genres_movie.insert(),
        [{"movie_id": movie_id, "genre_id": gid} for gid in genre_ids],
    )


def list_movies_detailed_filtered(
    db: Session,
    page: int,
    page_size: int,
    title: str | None = None,
    release_year: int | None = None,
    genre: str | None = None,
):
    # Build a base query that returns filtered Movie IDs only.
    # This keeps the count accurate and avoids heavy joins for pagination.
    base = select(Movie.id)

    # Apply filters with AND logic by chaining conditions.
    if title:
        # Case-insensitive partial match on title
        base = base.where(Movie.title.ilike(f"%{title}%"))

    if release_year is not None:
        base = base.where(Movie.release_year == release_year)

    if genre:
        # Filter movies that have a genre with the given name
        base = (
            base.join(genres_movie, genres_movie.c.movie_id == Movie.id)
            .join(Genre, Genre.id == genres_movie.c.genre_id)
            .where(Genre.name == genre)
        )

    # Ensure uniqueness when joins are involved (e.g., genre filter).
    base_subq = base.distinct().subquery()

    # Count total items AFTER filters
    total_items = db.scalar(select(func.count()).select_from(base_subq)) or 0

    # Apply pagination on filtered IDs
    offset = (page - 1) * page_size
    paged_ids = db.execute(
        select(base_subq.c.id).order_by(base_subq.c.id).offset(offset).limit(page_size)
    ).scalars().all()

    if not paged_ids:
        # No items on this page (or filters too restrictive)
        return int(total_items), [], {}

    # Aggregate ratings per movie (AVG + COUNT)
    ratings_agg = (
        select(
            MovieRating.movie_id.label("movie_id"),
            func.avg(MovieRating.score).label("avg_rating"),
            func.count(MovieRating.id).label("ratings_count"),
        )
        .group_by(MovieRating.movie_id)
        .subquery()
    )

    # Fetch Movie + Director + rating aggregates for the paged IDs
    rows = db.execute(
        select(Movie, Director, ratings_agg.c.avg_rating, ratings_agg.c.ratings_count)
        .join(Director, Movie.director_id == Director.id)
        .outerjoin(ratings_agg, ratings_agg.c.movie_id == Movie.id)
        .where(Movie.id.in_(paged_ids))
        .order_by(Movie.id)
    ).all()

    movies_pack = []
    movie_ids: list[int] = []

    for movie, director, avg_rating, ratings_count in rows:
        movies_pack.append(
            {
                "movie": movie,
                "director": director,
                "avg_rating": avg_rating,
                "ratings_count": ratings_count,
            }
        )
        movie_ids.append(movie.id)

    # Fetch genres for all movies in the current page in a single query
    genres_rows = db.execute(
        select(genres_movie.c.movie_id, Genre.name)
        .join(Genre, Genre.id == genres_movie.c.genre_id)
        .where(genres_movie.c.movie_id.in_(movie_ids))
    ).all()

    # Build a mapping: movie_id -> list of genre names
    genres_map: dict[int, list[str]] = {}
    for mid, gname in genres_rows:
        genres_map.setdefault(mid, []).append(gname)

    return int(total_items), movies_pack, genres_map


def get_movie_detail(db: Session, movie_id: int):
    # Fetch movie + director; if not found, return None
    row = db.execute(
        select(Movie, Director)
        .join(Director, Movie.director_id == Director.id)
        .where(Movie.id == movie_id)
    ).first()

    if row is None:
        return None

    movie, director = row

    # Aggregate ratings for the movie (AVG + COUNT)
    ratings_row = db.execute(
        select(
            func.avg(MovieRating.score).label("avg_rating"),
            func.count(MovieRating.id).label("ratings_count"),
        ).where(MovieRating.movie_id == movie_id)
    ).one()

    # Fetch genres for this movie
    genres = db.execute(
        select(Genre.name)
        .join(genres_movie, genres_movie.c.genre_id == Genre.id)
        .where(genres_movie.c.movie_id == movie_id)
    ).scalars().all()

    return {
        "movie": movie,
        "director": director,
        "genres": genres,
        "avg_rating": ratings_row.avg_rating,
        "ratings_count": ratings_row.ratings_count,
    }


# Backward-compatible alias to avoid import errors in older service code
list_movies_detailed = list_movies_detailed_filtered
