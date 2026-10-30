
from pathlib import Path

import numpy as np
import pandas as pd

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal, Base
from .model import SvdMovie, SvdRating


RATINGS_PATH = Path(
    "/Users/jeongtaegoon/Downloads/ratings.pkl"
)

MOVIES_PATH = Path(
    "/Users/jeongtaegoon/Downloads/movies.dat"
)

CHUNK_SIZE = 10000


def create_tables():
    Base.metadata.create_all(bind=engine)


def _upsert_movies(db: Session, rows: list[dict]):
    stmt = insert(SvdMovie).values(rows)

    stmt = stmt.on_conflict_do_update(
        index_elements=["movie_id"],
        set_={
            "title": stmt.excluded.title,
        },
    )

    db.execute(stmt)
    db.commit()


def import_movies():
    if not MOVIES_PATH.exists():
        raise FileNotFoundError(MOVIES_PATH)

    total = 0
    batch = []

    with SessionLocal() as db:
        with MOVIES_PATH.open(
            "r",
            encoding="latin-1",
        ) as file:

            for line in file:
                parts = line.rstrip("\r\n").split("::", 2)

                if len(parts) != 3:
                    continue

                movie_id, title, _genres = parts

                batch.append({
                    "movie_id": int(movie_id),
                    "title": title,
                })

                if len(batch) >= CHUNK_SIZE:
                    _upsert_movies(db, batch)
                    total += len(batch)
                    batch.clear()

            if batch:
                _upsert_movies(db, batch)
                total += len(batch)

    return total


def import_ratings():
    if not RATINGS_PATH.exists():
        raise FileNotFoundError(RATINGS_PATH)

    # pickle은 일반적으로 전체 역직렬화가 필요합니다.
    # 단, 고객×영화 밀집 피벗은 만들지 않습니다.
    frame = pd.read_pickle(RATINGS_PATH)

    required = {
        "userID",
        "movieID",
        "ratings",
    }

    if not required.issubset(frame.columns):
        raise ValueError(
            f"필수 열 누락: {required - set(frame.columns)}"
        )

    if "timestamp" in frame.columns:
        frame = frame.sort_values("timestamp")

    frame = frame.drop_duplicates(
        subset=["userID", "movieID"],
        keep="last",
    )

    frame = frame[
        ["userID", "movieID", "ratings"]
    ]

    total = len(frame)

    with SessionLocal() as db:
        for start in range(0, total, CHUNK_SIZE):
            chunk = frame.iloc[
                start:start + CHUNK_SIZE
            ]

            rows = [
                {
                    "user_id": int(user_id),
                    "movie_id": int(movie_id),
                    "rating": float(rating),
                }
                for user_id, movie_id, rating
                in chunk.itertuples(
                    index=False,
                    name=None,
                )
            ]

            stmt = insert(SvdRating).values(rows)

            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "user_id",
                    "movie_id",
                ],
                set_={
                    "rating": stmt.excluded.rating,
                },
            )

            db.execute(stmt)
            db.commit()

            print(
                f"\r평점 적재: "
                f"{min(start + CHUNK_SIZE, total):,}"
                f" / {total:,}",
                end="",
                flush=True,
            )

    print()
    return total


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


def get_movie_titles(
    movie_ids: list[int],
) -> dict[int, str]:

    if not movie_ids:
        return {}

    with SessionLocal() as db:
        rows = db.execute(
            select(
                SvdMovie.movie_id,
                SvdMovie.title,
            ).where(
                SvdMovie.movie_id.in_(movie_ids)
            )
        ).all()

        return {
            int(movie_id): title
            for movie_id, title in rows
        }
