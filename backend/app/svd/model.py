from sqlalchemy import BigInteger, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SvdMovie(Base):
    __tablename__ = "svd_movies"

    movie_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    genres: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )


class SvdRating(Base):
    __tablename__ = "svd_ratings"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    movie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("svd_movies.movie_id"),
        primary_key=True,
    )

    rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_svd_ratings_movie", "movie_id"),
    )