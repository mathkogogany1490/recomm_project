
import logging
import time

from sqlalchemy import bindparam, text
from sqlalchemy.exc import OperationalError

from app.database import SessionLocal


logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 3


def _fetch_all(sql, params=None):
    """DB 연결 오류 시 쿼리 단위로 재시도."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with SessionLocal() as db:
                return db.execute(
                    sql, params or {}
                ).fetchall()

        except OperationalError as exc:
            logger.warning(
                "PostgreSQL 오류 (%s/%s): %s",
                attempt,
                MAX_RETRIES,
                exc,
            )

            if attempt == MAX_RETRIES:
                raise

            time.sleep(RETRY_DELAY * attempt)


# ==========================================
# 1. PostgreSQL 데이터 건수
# ==========================================

def get_counts():
    with SessionLocal() as db:
        rating_count = db.scalar(text("""
            SELECT COUNT(*)
            FROM svd_ratings
            WHERE timestamp IS NOT NULL
        """))

        user_count = db.scalar(text("""
            SELECT COUNT(DISTINCT user_id)
            FROM svd_ratings
            WHERE timestamp IS NOT NULL
        """))

        movie_count = db.scalar(text("""
            SELECT COUNT(*)
            FROM svd_movies
        """))

    return {
        "rating_count": int(rating_count or 0),
        "user_count": int(user_count or 0),
        "movie_count": int(movie_count or 0),
    }


# ==========================================
# 2. 전체 영화 ID 조회
# ==========================================

def get_movie_ids():
    rows = _fetch_all(text("""
        SELECT movie_id
        FROM svd_movies
        ORDER BY movie_id
    """))

    return [int(row.movie_id) for row in rows]


# ==========================================
# 3. 고객별 시간순 평점 이력
# ==========================================

def iter_user_histories(batch_size=1000):
    """
    사용자 ID 기준 페이지 조회.

    - 페이지마다 연결 종료
    - 고객별 시간순 평점 이력 반환
    - 기존 반환 형식 유지:
        yield user_id, [(movie_id, rating), ...]

    주의:
    학습 중 svd_ratings가 변경되지 않는다는 전제.
    """

    if batch_size < 1:
        raise ValueError("batch_size는 1 이상이어야 합니다.")

    last_user_id = -1

    user_sql = text("""
        SELECT DISTINCT user_id
        FROM svd_ratings
        WHERE timestamp IS NOT NULL
          AND user_id > :last_user_id
        ORDER BY user_id
        LIMIT :batch_size
    """)

    history_sql = text("""
        SELECT
            user_id,
            movie_id,
            rating
        FROM svd_ratings
        WHERE user_id IN :user_ids
          AND timestamp IS NOT NULL
        ORDER BY
            user_id,
            timestamp,
            movie_id
    """).bindparams(
        bindparam("user_ids", expanding=True)
    )

    while True:
        user_rows = _fetch_all(
            user_sql,
            {
                "last_user_id": last_user_id,
                "batch_size": batch_size,
            },
        )

        if not user_rows:
            break

        user_ids = [
            int(row.user_id)
            for row in user_rows
        ]

        rows = _fetch_all(
            history_sql,
            {"user_ids": user_ids},
        )

        histories = {
            user_id: []
            for user_id in user_ids
        }

        for row in rows:
            histories[int(row.user_id)].append(
                (
                    int(row.movie_id),
                    float(row.rating),
                )
            )

        for user_id in user_ids:
            yield user_id, histories[user_id]

        last_user_id = user_ids[-1]


# ==========================================
# 4. 특정 고객 평점 이력
# ==========================================

def get_user_history(user_id):
    rows = _fetch_all(
        text("""
            SELECT movie_id, rating
            FROM svd_ratings
            WHERE user_id = :user_id
              AND timestamp IS NOT NULL
            ORDER BY timestamp, movie_id
        """),
        {"user_id": user_id},
    )

    return [
        (int(row.movie_id), float(row.rating))
        for row in rows
    ]


# ==========================================
# 5. 영화 제목 / 장르 조회
# ==========================================

def get_movie_details(movie_ids):
    if not movie_ids:
        return {}

    sql = text("""
        SELECT movie_id, title, genres
        FROM svd_movies
        WHERE movie_id IN :movie_ids
    """).bindparams(
        bindparam("movie_ids", expanding=True)
    )

    rows = _fetch_all(
        sql,
        {"movie_ids": list(movie_ids)},
    )

    return {
        int(row.movie_id): {
            "title": row.title,
            "genres": row.genres or "",
        }
        for row in rows
    }
