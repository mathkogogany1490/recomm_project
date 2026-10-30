import numpy as np

from sqlalchemy import select

from app.database import SessionLocal
from app.svd.model import SvdMovie, SvdRating


def iter_ratings(batch_size=50000):
    stmt = (
        select(
            SvdRating.user_id,
            SvdRating.movie_id,
            SvdRating.rating,
        )
        .execution_options(
            yield_per=batch_size,
            stream_results=True,
        )
    )

    with SessionLocal() as db:
        result = db.execute(stmt)

        for batch in result.partitions(batch_size):
            yield np.asarray(
                batch,
                dtype=np.float64,
            )


def get_seen_movie_ids(user_id: int) -> set[int]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(SvdRating.movie_id).where(
                SvdRating.user_id == user_id
            )
        ).all()

        return set(rows)


def get_movie_details(movie_ids: list[int]) -> dict:
    if not movie_ids:
        return {}

    with SessionLocal() as db:
        rows = db.execute(
            select(
                SvdMovie.movie_id,
                SvdMovie.title,
                SvdMovie.genres,
            ).where(
                SvdMovie.movie_id.in_(movie_ids)
            )
        ).all()

        return {
            int(movie_id): {
                "title": title,
                "genres": genres or "",
            }
            for movie_id, title, genres in rows
        }