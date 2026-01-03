from sqlalchemy import Column, ForeignKey, Integer, Table
from app.db.base import Base

genres_movie = Table(
    "genres_movie",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)
