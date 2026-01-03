from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.movie_genre import genres_movie

class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    director_id: Mapped[int] = mapped_column(ForeignKey("directors.id", ondelete="RESTRICT"), nullable=False)
    release_year: Mapped[int] = mapped_column(Integer, nullable=False)
    cast: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    director = relationship("Director", back_populates="movies")
    genres = relationship("Genre", secondary=genres_movie, back_populates="movies")
    ratings = relationship("MovieRating", back_populates="movie", cascade="all, delete-orphan")
