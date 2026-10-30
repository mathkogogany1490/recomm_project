
import argparse
import os
import tempfile

from functools import lru_cache
from pathlib import Path

import numpy as np

from scipy.sparse import coo_matrix
from scipy.sparse.linalg import svds

from . import repository


# ==========================================
# 1. 설정
# ==========================================

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "svd_model"
    / ".svd_model.npz"
)

FACTORS = 30
PREDICTION_BATCH = 100000


# ==========================================
# 2. SVD 모델 학습
# ==========================================

def train_model():
    user_parts = []
    movie_parts = []
    rating_parts = []

    print("\n========== SVD 학습 시작 ==========")
    print("PostgreSQL 평점 데이터 읽기")

    # 기존 PostgreSQL 데이터 사용
    for batch in repository.iter_ratings():
        if len(batch) == 0:
            continue

        user_parts.append(
            batch[:, 0].astype(np.int64)
        )

        movie_parts.append(
            batch[:, 1].astype(np.int64)
        )

        rating_parts.append(
            batch[:, 2].astype(np.float32)
        )

    if not user_parts:
        raise ValueError(
            "PostgreSQL에 학습할 평점 데이터가 없습니다."
        )

    user_ids_raw = np.concatenate(user_parts)
    movie_ids_raw = np.concatenate(movie_parts)
    ratings = np.concatenate(rating_parts)

    del user_parts
    del movie_parts
    del rating_parts

    user_ids, user_indices = np.unique(
        user_ids_raw,
        return_inverse=True,
    )

    movie_ids, movie_indices = np.unique(
        movie_ids_raw,
        return_inverse=True,
    )

    del user_ids_raw
    del movie_ids_raw

    user_indices = user_indices.astype(np.int32)
    movie_indices = movie_indices.astype(np.int32)

    user_count = len(user_ids)
    movie_count = len(movie_ids)
    rating_count = len(ratings)

    k = min(
        FACTORS,
        user_count - 1,
        movie_count - 1,
    )

    if k < 1:
        raise ValueError(
            "고객과 영화가 각각 2개 이상 필요합니다."
        )

    print(
        f"고객 {user_count:,}명, "
        f"영화 {movie_count:,}편, "
        f"평점 {rating_count:,}건"
    )

    # ======================================
    # 3. 희소 행렬 생성
    # ======================================

    sparse_matrix = coo_matrix(
        (
            ratings,
            (
                user_indices,
                movie_indices,
            ),
        ),
        shape=(
            user_count,
            movie_count,
        ),
        dtype=np.float32,
    ).tocsr()

    print(f"희소 SVD 학습 시작 (k={k})")

    U, singular_values, Vt = svds(
        sparse_matrix,
        k=k,
        which="LM",
        random_state=42,
    )

    order = np.argsort(
        singular_values
    )[::-1]

    U = U[:, order]
    singular_values = singular_values[order]
    Vt = Vt[order, :]

    sqrt_s = np.sqrt(singular_values)

    user_factors = (
        U * sqrt_s
    ).astype(np.float32)

    movie_factors = (
        Vt.T * sqrt_s
    ).astype(np.float32)

    del sparse_matrix
    del U
    del Vt

    # ======================================
    # 4. MAE / MSE / RMSE 계산
    # ======================================

    absolute_error_sum = 0.0
    squared_error_sum = 0.0

    print("MAE / MSE / RMSE 계산 시작")

    for start in range(
        0,
        rating_count,
        PREDICTION_BATCH,
    ):
        end = min(
            start + PREDICTION_BATCH,
            rating_count,
        )

        u = user_indices[start:end]
        m = movie_indices[start:end]

        predicted = np.einsum(
            "ij,ij->i",
            user_factors[u],
            movie_factors[m],
        )

        predicted = np.clip(
            predicted,
            1.0,
            5.0,
        )

        actual = ratings[
            start:end
        ].astype(np.float64)

        error = (
            actual
            - predicted.astype(np.float64)
        )

        absolute_error_sum += float(
            np.abs(error).sum()
        )

        squared_error_sum += float(
            np.square(error).sum()
        )

    mae = absolute_error_sum / rating_count
    mse = squared_error_sum / rating_count
    rmse = float(np.sqrt(mse))

    # ======================================
    # 5. 모델 저장
    # ======================================

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        dir=MODEL_PATH.parent,
        suffix=".npz",
        delete=False,
    ) as temp:
        temp_path = Path(temp.name)

    try:
        np.savez_compressed(
            temp_path,
            user_ids=user_ids,
            movie_ids=movie_ids,
            user_factors=user_factors,
            movie_factors=movie_factors,
            mae=np.float64(mae),
            mse=np.float64(mse),
            rmse=np.float64(rmse),
            rating_count=np.int64(
                rating_count
            ),
            factors=np.int64(k),
        )

        os.replace(
            temp_path,
            MODEL_PATH,
        )

    finally:
        temp_path.unlink(
            missing_ok=True
        )

    load_model.cache_clear()

    print()
    print("========== SVD 학습 완료 ==========")
    print(f"MAE  : {mae:.6f}")
    print(f"MSE  : {mse:.6f}")
    print(f"RMSE : {rmse:.6f}")
    print(f"모델 저장: {MODEL_PATH}")
    print("===================================")

    return {
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
    }


# ==========================================
# 6. 학습된 모델 불러오기
# ==========================================

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "SVD 모델이 없습니다. "
            "먼저 학습을 실행하세요."
        )

    with np.load(
        MODEL_PATH,
        allow_pickle=False,
    ) as data:
        model = {
            key: data[key].copy()
            for key in data.files
        }

    required = {
        "mae",
        "mse",
        "rmse",
        "user_ids",
        "movie_ids",
        "user_factors",
        "movie_factors",
        "rating_count",
        "factors",
    }

    missing = required - set(model)

    if missing:
        raise FileNotFoundError(
            "이전 형식의 SVD 모델입니다. "
            "다시 학습하세요. "
            f"누락된 항목: {sorted(missing)}"
        )

    return model


# ==========================================
# 7. KPI 조회
# ==========================================

def get_kpi():
    model = load_model()

    return {
        "mae": round(
            float(model["mae"]), 6
        ),
        "mse": round(
            float(model["mse"]), 6
        ),
        "rmse": round(
            float(model["rmse"]), 6
        ),
        "rating_count": int(
            model["rating_count"]
        ),
        "user_count": len(
            model["user_ids"]
        ),
        "movie_count": len(
            model["movie_ids"]
        ),
        "factors": int(
            model["factors"]
        ),
        "evaluation": "training_observed_error",
    }


# ==========================================
# 8. 추천 영화 TOP 5
# ==========================================

def get_recommendations(user_id: int):
    model = load_model()

    user_ids = model["user_ids"]
    movie_ids = model["movie_ids"]

    user_pos = int(
        np.searchsorted(
            user_ids,
            user_id,
        )
    )

    if (
        user_pos >= len(user_ids)
        or int(user_ids[user_pos]) != user_id
    ):
        raise ValueError(
            "학습 데이터에 없는 고객 아이디입니다."
        )

    user_vector = (
        model["user_factors"][user_pos]
    )

    movie_factors = (
        model["movie_factors"]
    )

    predicted = (
        movie_factors @ user_vector
    )

    predicted = np.clip(
        predicted,
        1.0,
        5.0,
    )

    seen_ids = (
        repository.get_seen_movie_ids(
            user_id
        )
    )

    unseen_mask = ~np.isin(
        movie_ids,
        list(seen_ids),
    )

    candidate_indices = (
        np.flatnonzero(unseen_mask)
    )

    if len(candidate_indices) == 0:
        return {
            "user_id": user_id,
            "recommendations": [],
        }

    candidate_scores = (
        predicted[candidate_indices]
    )

    top_count = min(
        5,
        len(candidate_indices),
    )

    top_local = np.argpartition(
        -candidate_scores,
        top_count - 1,
    )[:top_count]

    top_indices = (
        candidate_indices[top_local]
    )

    top_indices = sorted(
        top_indices,
        key=lambda idx: (
            -float(predicted[idx]),
            int(movie_ids[idx]),
        ),
    )

    selected_movie_ids = [
        int(movie_ids[idx])
        for idx in top_indices
    ]

    titles = (
        repository.get_movie_titles(
            selected_movie_ids
        )
    )

    recommendations = []

    for rank, idx in enumerate(
        top_indices,
        start=1,
    ):
        movie_id = int(
            movie_ids[idx]
        )

        recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": titles.get(
                movie_id,
                f"영화 {movie_id}",
            ),
            "predicted_rating": round(
                float(predicted[idx]),
                4,
            ),
        })

    return {
        "user_id": user_id,
        "recommendations": recommendations,
    }


# ==========================================
# 9. CLI - 학습만 실행
# ==========================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=["train"],
        help="PostgreSQL 데이터로 SVD 모델 학습",
    )

    args = parser.parse_args()

    if args.command == "train":
        train_model()


if __name__ == "__main__":
    main()
