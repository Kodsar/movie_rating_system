from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Movie, Director, Genre, MovieRating
from app.models.movie_genre import genres_movie


def get_movie_by_id(db: Session, movie_id: int) -> Movie | None:
    # Fetch movie row by id
    return db.execute(select(Movie).where(Movie.id == movie_id)).scalar_one_or_none()


def get_director_by_id(db: Session, director_id: int) -> Director | None:
    # Fetch director by id
    return db.execute(select(Director).where(Director.id == director_id)).scalar_one_or_none()


def get_genres_by_ids(db: Session, genre_ids: list[int]) -> list[Genre]:
    # Fetch all genres matching the given IDs
    if not genre_ids:
        return []
    return db.execute(select(Genre).where(Genre.id.in_(genre_ids))).scalars().all()


def create_movie(db: Session, title: str, director_id: int, release_year: int, cast: str | None) -> Movie:
    # Create Movie row (flush to get ID without committing)
    movie = Movie(title=title, director_id=director_id, release_year=release_year, cast=cast)
    db.add(movie)
    db.flush()
    return movie


def insert_movie_genres(db: Session, movie_id: int, genre_ids: list[int]) -> None:
    # Insert association rows into genres_movie
    if not genre_ids:
        return
    db.execute(
        genres_movie.insert(),
        [{"movie_id": movie_id, "genre_id": gid} for gid in genre_ids],
    )


def update_movie_fields(
    db: Session,
    movie: Movie,
    title: str,
    director_id: int,
    release_year: int,
    cast: str | None,
) -> Movie:
    # Update mutable fields on the Movie ORM object
    movie.title = title
    movie.director_id = director_id
    movie.release_year = release_year
    movie.cast = cast
    db.add(movie)
    db.flush()
    return movie


def replace_movie_genres(db: Session, movie_id: int, genre_ids: list[int]) -> None:
    # Replace all existing genres for the movie with the provided list
    db.execute(delete(genres_movie).where(genres_movie.c.movie_id == movie_id))
    if not genre_ids:
        return
    db.execute(
        genres_movie.insert(),
        [{"movie_id": movie_id, "genre_id": gid} for gid in genre_ids],
    )


def delete_movie(db: Session, movie_id: int) -> bool:
    # Delete movie and related rows (ratings + association table)
    movie = get_movie_by_id(db, movie_id)
    if movie is None:
        return False

    db.execute(delete(MovieRating).where(MovieRating.movie_id == movie_id))
    db.execute(delete(genres_movie).where(genres_movie.c.movie_id == movie_id))
    db.execute(delete(Movie).where(Movie.id == movie_id))
    return True


def create_movie_rating(db: Session, movie_id: int, score: int) -> MovieRating:
    # Insert a new rating row for a movie
    rating = MovieRating(movie_id=movie_id, score=score)
    db.add(rating)
    db.flush()  # ensures rating.id is generated
    return rating


def get_movie_rating_stats(db: Session, movie_id: int) -> tuple[float | None, int]:
    # Compute average rating and ratings count for a single movie
    avg_score, cnt = db.execute(
        select(func.avg(MovieRating.score), func.count(MovieRating.id))
        .where(MovieRating.movie_id == movie_id)
    ).one()

    avg = float(avg_score) if avg_score is not None else None
    count = int(cnt or 0)
    return avg, count


def list_movies_detailed_filtered(
    db: Session,
    page: int,
    page_size: int,
    title: str | None = None,
    release_year: int | None = None,
    genre: str | None = None,
):
    # Build a base query that returns filtered Movie IDs only.
    base = select(Movie.id)

    if title:
        base = base.where(Movie.title.ilike(f"%{title}%"))

    if release_year is not None:
        base = base.where(Movie.release_year == release_year)

    if genre:
        base = (
            base.join(genres_movie, genres_movie.c.movie_id == Movie.id)
            .join(Genre, Genre.id == genres_movie.c.genre_id)
            .where(Genre.name == genre)
        )

    base_subq = base.distinct().subquery()

    total_items = db.scalar(select(func.count()).select_from(base_subq)) or 0

    offset = (page - 1) * page_size
    paged_ids = db.execute(
        select(base_subq.c.id).order_by(base_subq.c.id).offset(offset).limit(page_size)
    ).scalars().all()

    if not paged_ids:
        return int(total_items), [], {}

    ratings_agg = (
        select(
            MovieRating.movie_id.label("movie_id"),
            func.avg(MovieRating.score).label("avg_rating"),
            func.count(MovieRating.id).label("ratings_count"),
        )
        .group_by(MovieRating.movie_id)
        .subquery()
    )

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

    genres_rows = db.execute(
        select(genres_movie.c.movie_id, Genre.name)
        .join(Genre, Genre.id == genres_movie.c.genre_id)
        .where(genres_movie.c.movie_id.in_(movie_ids))
    ).all()

    genres_map: dict[int, list[str]] = {}
    for mid, gname in genres_rows:
        genres_map.setdefault(mid, []).append(gname)

    return int(total_items), movies_pack, genres_map


def get_movie_detail(db: Session, movie_id: int):
    row = db.execute(
        select(Movie, Director)
        .join(Director, Movie.director_id == Director.id)
        .where(Movie.id == movie_id)
    ).first()

    if row is None:
        return None

    movie, director = row

    ratings_row = db.execute(
        select(
            func.avg(MovieRating.score).label("avg_rating"),
            func.count(MovieRating.id).label("ratings_count"),
        ).where(MovieRating.movie_id == movie_id)
    ).one()

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


# Backward-compatible alias (optional)
list_movies_detailed = list_movies_detailed_filtered
