
from sqlalchemy import text

from app.database import SessionLocal


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
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT movie_id
            FROM svd_movies
            ORDER BY movie_id
        """))

        return [
            int(row.movie_id)
            for row in result
        ]


# ==========================================
# 3. 고객별 시간순 평점 이력
# ==========================================

def iter_user_histories(batch_size=50000):
    """
    PostgreSQL에서 고객별 영화 평점 이력을
    시간순으로 스트리밍합니다.

    전체 평점 데이터를 메모리에 올리거나
    고객×영화 피벗을 생성하지 않습니다.
    """

    sql = text("""
        SELECT
            user_id,
            movie_id,
            rating
        FROM svd_ratings
        WHERE timestamp IS NOT NULL
        ORDER BY
            user_id,
            timestamp,
            movie_id
    """).execution_options(
        stream_results=True,
        yield_per=batch_size,
    )

    with SessionLocal() as db:
        result = db.execute(sql)

        current_user = None
        history = []

        for row in result:
            user_id = int(row.user_id)
            movie_id = int(row.movie_id)
            rating = float(row.rating)

            if (
                current_user is not None
                and user_id != current_user
            ):
                yield current_user, history
                history = []

            current_user = user_id

            history.append((
                movie_id,
                rating,
            ))

        if current_user is not None:
            yield current_user, history


# ==========================================
# 4. 특정 고객의 평점 이력
# ==========================================

def get_user_history(user_id):
    with SessionLocal() as db:
        result = db.execute(
            text("""
                SELECT
                    movie_id,
                    rating
                FROM svd_ratings
                WHERE user_id = :user_id
                  AND timestamp IS NOT NULL
                ORDER BY
                    timestamp,
                    movie_id
            """),
            {"user_id": user_id},
        )

        return [
            (
                int(row.movie_id),
                float(row.rating),
            )
            for row in result
        ]


# ==========================================
# 5. 영화 제목 / 장르 조회
# ==========================================

def get_movie_details(movie_ids):
    if not movie_ids:
        return {}

    sql = text("""
        SELECT
            movie_id,
            title,
            genres
        FROM svd_movies
        WHERE movie_id IN :movie_ids
    """).bindparams(
        __import__(
            "sqlalchemy"
        ).bindparam(
            "movie_ids",
            expanding=True,
        )
    )

    with SessionLocal() as db:
        result = db.execute(
            sql,
            {"movie_ids": list(movie_ids)},
        )

        return {
            int(row.movie_id): {
                "title": row.title,
                "genres": row.genres or "",
            }
            for row in result
        }
