from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Movie, Director, Genre, MovieRating
from app.models.movie_genre import genres_movie


def list_movies_detailed(
    db: Session,
    page: int,
    page_size: int,
    title: str | None = None,
    release_year: int | None = None,
    genre: str | None = None,
):
    # Calculate pagination offset/limit
    offset = (page - 1) * page_size

    # Base query for filtering movies (AND logic by chaining where())
    base_movies = select(Movie.id)

    if title:
        # Case-insensitive "contains" search
        base_movies = base_movies.where(Movie.title.ilike(f"%{title}%"))

    if release_year is not None:
        base_movies = base_movies.where(Movie.release_year == release_year)

    if genre:
        # Filter movies by genre name through association table
        base_movies = (
            base_movies.join(genres_movie, genres_movie.c.movie_id == Movie.id)
            .join(Genre, Genre.id == genres_movie.c.genre_id)
            .where(Genre.name.ilike(genre))
        )

    filtered_ids_subq = base_movies.subquery()

    # Total items AFTER filters
    total_items = db.scalar(select(func.count()).select_from(filtered_ids_subq)) or 0

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

    # Fetch page of movies (only filtered ones)
    rows = db.execute(
        select(
            Movie,
            Director,
            ratings_agg.c.avg_rating,
            ratings_agg.c.ratings_count,
        )
        .join(filtered_ids_subq, filtered_ids_subq.c.id == Movie.id)
        .join(Director, Movie.director_id == Director.id)
        .outerjoin(ratings_agg, ratings_agg.c.movie_id == Movie.id)
        .order_by(Movie.id)
        .offset(offset)
        .limit(page_size)
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

    # Fetch genres for movies in this page in a single query
    genres_rows = []
    if movie_ids:
        genres_rows = db.execute(
            select(genres_movie.c.movie_id, Genre.name)
            .join(Genre, Genre.id == genres_movie.c.genre_id)
            .where(genres_movie.c.movie_id.in_(movie_ids))
        ).all()

    # Build movie_id -> [genre names]
    genres_map: dict[int, list[str]] = {}
    for mid, gname in genres_rows:
        genres_map.setdefault(mid, []).append(gname)

    return total_items, movies_pack, genres_map
