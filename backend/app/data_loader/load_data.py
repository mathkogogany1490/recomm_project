
from pathlib import Path

import pandas as pd

from sqlalchemy import text
from tqdm import tqdm

from app.database import SessionLocal


# ==========================================
# 1. 경로 및 설정
# ==========================================
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

RATINGS_PATH = DATA_DIR / "ratings.pkl"
MOVIES_PATH = DATA_DIR / "movies.dat"

BATCH_SIZE = 10000


# ==========================================
# 2. 테이블 준비
# ==========================================

def prepare_tables():
    print("\n[1/4] PostgreSQL 테이블 준비")

    with SessionLocal() as db:
        # 기존 SVD/MF/Transformer가 참조하는
        # 테이블 이름은 그대로 유지
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS svd_movies (
                movie_id BIGINT PRIMARY KEY,
                title TEXT NOT NULL,
                genres TEXT
            )
        """))

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS svd_ratings (
                user_id BIGINT NOT NULL,
                movie_id BIGINT NOT NULL,
                rating DOUBLE PRECISION NOT NULL,
                timestamp BIGINT,
                PRIMARY KEY (user_id, movie_id)
            )
        """))

        # 기존 테이블에 없는 컬럼 추가
        db.execute(text("""
            ALTER TABLE svd_movies
            ADD COLUMN IF NOT EXISTS genres TEXT
        """))

        db.execute(text("""
            ALTER TABLE svd_ratings
            ADD COLUMN IF NOT EXISTS timestamp BIGINT
        """))

        db.commit()

    print("테이블 준비 완료")


# ==========================================
# 3. 기존 데이터 삭제
# ==========================================

def clear_existing_data():
    print("\n[2/4] 기존 데이터 삭제")

    with SessionLocal() as db:
        # 외래키 참조를 고려해 평점부터 삭제
        db.execute(text("""
            DELETE FROM svd_ratings
        """))

        db.execute(text("""
            DELETE FROM svd_movies
        """))

        db.commit()

    print("기존 영화 및 평점 데이터 삭제 완료")


# ==========================================
# 4. 영화 데이터 적재
# ==========================================

def load_movies():
    print("\n[3/4] 영화 데이터 적재")

    if not MOVIES_PATH.exists():
        raise FileNotFoundError(
            f"movies.dat 파일이 없습니다: {MOVIES_PATH}"
        )

    movies = []

    with MOVIES_PATH.open(
        "r",
        encoding="latin-1",
    ) as file:
        for line in file:
            parts = line.strip().split("::", 2)

            if len(parts) != 3:
                continue

            movie_id, title, genres = parts

            movies.append({
                "movie_id": int(movie_id),
                "title": title,
                "genres": genres,
            })

    insert_sql = text("""
        INSERT INTO svd_movies (
            movie_id,
            title,
            genres
        )
        VALUES (
            :movie_id,
            :title,
            :genres
        )
    """)

    with SessionLocal() as db:
        for start in tqdm(
            range(0, len(movies), BATCH_SIZE),
            desc="영화 적재",
            unit="batch",
        ):
            chunk = movies[
                start:start + BATCH_SIZE
            ]

            db.execute(insert_sql, chunk)
            db.commit()

    print(f"영화 적재 완료: {len(movies):,}편")


# ==========================================
# 5. 평점 데이터 적재
# ==========================================

def load_ratings():
    print("\n[4/4] 평점 데이터 적재")

    if not RATINGS_PATH.exists():
        raise FileNotFoundError(
            f"ratings.pkl 파일이 없습니다: {RATINGS_PATH}"
        )

    print("ratings.pkl 파일 읽는 중...")

    df = pd.read_pickle(RATINGS_PATH)

    required_columns = {
        "userID",
        "movieID",
        "ratings",
        "timestamp",
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"필요한 컬럼: {sorted(required_columns)}"
        )

    df = df[
        ["userID", "movieID", "ratings", "timestamp"]
    ].copy()

    df = df.dropna()

    df = df.astype({
        "userID": "int64",
        "movieID": "int64",
        "ratings": "float32",
        "timestamp": "int64",
    })

    # 동일 고객/영화 중복 평가가 있다면
    # 최신 timestamp의 평점만 저장
    df = (
        df.sort_values(
            "timestamp",
            kind="stable",
        )
        .drop_duplicates(
            ["userID", "movieID"],
            keep="last",
        )
    )

    total = len(df)

    print(f"적재할 평점: {total:,}건")

    insert_sql = text("""
        INSERT INTO svd_ratings (
            user_id,
            movie_id,
            rating,
            timestamp
        )
        VALUES (
            :user_id,
            :movie_id,
            :rating,
            :timestamp
        )
    """)

    with SessionLocal() as db:
        for start in tqdm(
            range(0, total, BATCH_SIZE),
            desc="평점 적재",
            unit="batch",
        ):
            chunk = df.iloc[
                start:start + BATCH_SIZE
            ]

            rows = [
                {
                    "user_id": int(user_id),
                    "movie_id": int(movie_id),
                    "rating": float(rating),
                    "timestamp": int(timestamp),
                }
                for user_id, movie_id, rating, timestamp
                in chunk.itertuples(
                    index=False,
                    name=None,
                )
            ]

            db.execute(insert_sql, rows)
            db.commit()

    print(f"평점 적재 완료: {total:,}건")


# ==========================================
# 6. 적재 결과 확인
# ==========================================

def verify_data():
    print("\n========== 적재 결과 ==========")

    with SessionLocal() as db:
        movie_count = db.scalar(text("""
            SELECT COUNT(*)
            FROM svd_movies
        """))

        rating_count = db.scalar(text("""
            SELECT COUNT(*)
            FROM svd_ratings
        """))

        timestamp_count = db.scalar(text("""
            SELECT COUNT(timestamp)
            FROM svd_ratings
        """))

        genre_count = db.scalar(text("""
            SELECT COUNT(genres)
            FROM svd_movies
        """))

    print(f"영화 수       : {movie_count:,}")
    print(f"평점 수       : {rating_count:,}")
    print(f"timestamp 수  : {timestamp_count:,}")
    print(f"장르 수       : {genre_count:,}")
    print("================================")


# ==========================================
# 7. 실행
# ==========================================

def main():
    print("================================")
    print(" PostgreSQL 영화/평점 데이터 적재")
    print("================================")

    # 원본 파일 존재 여부를 삭제 전에 확인
    if not RATINGS_PATH.exists():
        raise FileNotFoundError(RATINGS_PATH)

    if not MOVIES_PATH.exists():
        raise FileNotFoundError(MOVIES_PATH)

    prepare_tables()
    clear_existing_data()

    load_movies()
    load_ratings()

    verify_data()

    print("\n모든 데이터 적재 완료")


if __name__ == "__main__":
    main()
