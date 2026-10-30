
import argparse
import os
import tempfile

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm

from . import repository
from .model import MatrixFactorization


# ==========================================
# 1. 설정
# ==========================================

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "mf_model"
    / "mf_model.pt"
)

FACTORS = 30
EPOCHS = 10
BATCH_SIZE = 8192
LEARNING_RATE = 0.003
WEIGHT_DECAY = 1e-5
VALIDATION_RATIO = 0.1
SEED = 42


# ==========================================
# 2. 학습 장치 자동 선택
# CUDA -> MPS -> CPU
# ==========================================

def get_device():
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(
            f"학습 장치: CUDA GPU "
            f"({torch.cuda.get_device_name(0)})"
        )

    elif (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        device = torch.device("mps")
        print("학습 장치: Apple MPS GPU")

    else:
        device = torch.device("cpu")
        print("학습 장치: CPU")

    return device


# ==========================================
# 3. 검증 함수
# MPS는 float64를 지원하지 않으므로
# CPU에서 float64로 오차를 누적
# ==========================================

def evaluate_model(model, val_loader, device):
    model.eval()

    absolute_error_sum = 0.0
    squared_error_sum = 0.0
    validation_count = 0

    with torch.no_grad():
        for users, movies, actual in val_loader:
            users = users.to(device)
            movies = movies.to(device)
            actual = actual.to(device)

            predicted = model(users, movies)
            predicted = predicted.clamp(1.0, 5.0)

            error = actual - predicted

            # GPU/MPS에서는 float32 사용
            # CPU로 이동한 뒤 float64로 합산
            error_cpu = error.detach().to("cpu")

            absolute_error_sum += (
                error_cpu.abs().double().sum().item()
            )

            squared_error_sum += (
                error_cpu.double().square().sum().item()
            )

            validation_count += len(actual)

    if validation_count == 0:
        raise ValueError("검증 데이터가 없습니다.")

    mae = absolute_error_sum / validation_count
    mse = squared_error_sum / validation_count
    rmse = float(np.sqrt(mse))

    return mae, mse, rmse


# ==========================================
# 4. MF 모델 학습
# ==========================================

def train_model():
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    print("\n========== MF 학습 시작 ==========")

    # --------------------------------------
    # PostgreSQL 평점 데이터 읽기
    # --------------------------------------

    user_parts = []
    movie_parts = []
    rating_parts = []

    print("PostgreSQL 평점 데이터 읽기")

    for batch in tqdm(
        repository.iter_ratings(),
        desc="평점 조회",
        unit="배치",
    ):
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

    del user_parts, movie_parts, rating_parts

    # --------------------------------------
    # 고객/영화 ID 인덱스 변환
    # --------------------------------------

    user_ids, user_indices = np.unique(
        user_ids_raw,
        return_inverse=True,
    )

    movie_ids, movie_indices = np.unique(
        movie_ids_raw,
        return_inverse=True,
    )

    del user_ids_raw, movie_ids_raw

    user_count = len(user_ids)
    movie_count = len(movie_ids)
    rating_count = len(ratings)

    if user_count < 2 or movie_count < 2:
        raise ValueError(
            "고객과 영화가 각각 2개 이상 필요합니다."
        )

    print(f"고객 수: {user_count:,}명")
    print(f"영화 수: {movie_count:,}편")
    print(f"평점 수: {rating_count:,}건")

    # --------------------------------------
    # 학습/검증 데이터 분리
    # --------------------------------------

    rng = np.random.default_rng(SEED)

    shuffled = rng.permutation(rating_count)

    val_size = max(
        1,
        int(rating_count * VALIDATION_RATIO),
    )

    val_idx = shuffled[:val_size]
    train_idx = shuffled[val_size:]

    if len(train_idx) == 0:
        raise ValueError("학습 데이터가 부족합니다.")

    # 검증 고객/영화가 학습 데이터에
    # 존재하는 경우만 평가
    train_user_seen = np.zeros(
        user_count,
        dtype=bool,
    )

    train_movie_seen = np.zeros(
        movie_count,
        dtype=bool,
    )

    train_user_seen[
        user_indices[train_idx]
    ] = True

    train_movie_seen[
        movie_indices[train_idx]
    ] = True

    valid_mask = (
        train_user_seen[user_indices[val_idx]]
        & train_movie_seen[movie_indices[val_idx]]
    )

    val_idx = val_idx[valid_mask]

    if len(val_idx) == 0:
        raise ValueError(
            "검증 가능한 평점 데이터가 없습니다."
        )

    print(f"학습 평점: {len(train_idx):,}건")
    print(f"검증 평점: {len(val_idx):,}건")

    # --------------------------------------
    # TensorDataset 생성
    # --------------------------------------

    train_dataset = TensorDataset(
        torch.from_numpy(
            user_indices[train_idx].astype(np.int64)
        ),
        torch.from_numpy(
            movie_indices[train_idx].astype(np.int64)
        ),
        torch.from_numpy(
            ratings[train_idx].astype(np.float32)
        ),
    )

    val_dataset = TensorDataset(
        torch.from_numpy(
            user_indices[val_idx].astype(np.int64)
        ),
        torch.from_numpy(
            movie_indices[val_idx].astype(np.int64)
        ),
        torch.from_numpy(
            ratings[val_idx].astype(np.float32)
        ),
    )

    del user_indices, movie_indices, ratings
    del shuffled, train_idx, val_idx

    # --------------------------------------
    # DataLoader
    # --------------------------------------

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    # --------------------------------------
    # 장치 선택 및 모델 생성
    # --------------------------------------

    device = get_device()

    model = MatrixFactorization(
        num_users=user_count,
        num_movies=movie_count,
        factors=FACTORS,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    criterion = torch.nn.MSELoss()

    # 전역 평균 평점 초기화
    with torch.no_grad():
        global_mean = (
            train_dataset.tensors[2]
            .double()
            .mean()
            .item()
        )

        model.global_bias.fill_(
            float(global_mean)
        )

    # --------------------------------------
    # Epoch 학습
    # --------------------------------------

    history = []

    for epoch in range(EPOCHS):
        model.train()

        train_loss_sum = 0.0
        train_count = 0

        progress = tqdm(
            train_loader,
            desc=f"Epoch {epoch + 1}/{EPOCHS}",
            unit="batch",
        )

        for users, movies, actual in progress:
            users = users.to(device)
            movies = movies.to(device)
            actual = actual.to(device)

            optimizer.zero_grad()

            predicted = model(users, movies)

            loss = criterion(
                predicted,
                actual,
            )

            loss.backward()
            optimizer.step()

            batch_count = len(actual)

            train_loss_sum += (
                loss.item() * batch_count
            )

            train_count += batch_count

            progress.set_postfix(
                train_mse=(
                    f"{train_loss_sum / train_count:.6f}"
                )
            )

        # ----------------------------------
        # 검증 MAE / MSE / RMSE
        # ----------------------------------

        mae, mse, rmse = evaluate_model(
            model,
            val_loader,
            device,
        )

        train_mse = train_loss_sum / train_count

        history.append({
            "epoch": epoch + 1,
            "train_mse": float(train_mse),
            "val_mae": float(mae),
            "val_mse": float(mse),
            "val_rmse": float(rmse),
        })

        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Train MSE={train_mse:.6f} | "
            f"Val MAE={mae:.6f} | "
            f"Val MSE={mse:.6f} | "
            f"Val RMSE={rmse:.6f}"
        )

    # --------------------------------------
    # 체크포인트 저장
    # --------------------------------------

    model_cpu = model.to("cpu")

    checkpoint = {
        "state_dict": model_cpu.state_dict(),
        "user_ids": torch.from_numpy(
            user_ids.copy()
        ),
        "movie_ids": torch.from_numpy(
            movie_ids.copy()
        ),
        "factors": FACTORS,
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
        "rating_count": int(rating_count),
        "validation_count": int(
            len(val_dataset)
        ),
        "history": history,
        "evaluation": "validation_holdout_10pct",
    }

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.NamedTemporaryFile(
        dir=MODEL_PATH.parent,
        suffix=".pt",
        delete=False,
    ) as temp:
        temp_path = Path(temp.name)

    try:
        torch.save(
            checkpoint,
            temp_path,
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

    print("\n========== MF 학습 완료 ==========")
    print(f"MAE  : {mae:.6f}")
    print(f"MSE  : {mse:.6f}")
    print(f"RMSE : {rmse:.6f}")
    print(f"모델 저장: {MODEL_PATH}")
    print("==================================")

    return {
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
    }


# ==========================================
# 5. 저장된 MF 모델 로드
# ==========================================

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "MF 모델이 없습니다. 먼저 학습하세요."
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )

    user_ids = checkpoint["user_ids"].numpy()
    movie_ids = checkpoint["movie_ids"].numpy()

    model = MatrixFactorization(
        num_users=len(user_ids),
        num_movies=len(movie_ids),
        factors=int(checkpoint["factors"]),
    )

    model.load_state_dict(
        checkpoint["state_dict"]
    )

    model.eval()

    return {
        "model": model,
        "user_ids": user_ids,
        "movie_ids": movie_ids,
        "mae": checkpoint["mae"],
        "mse": checkpoint["mse"],
        "rmse": checkpoint["rmse"],
        "rating_count": checkpoint["rating_count"],
        "factors": checkpoint["factors"],
        "evaluation": checkpoint["evaluation"],
    }


# ==========================================
# 6. KPI 조회
# ==========================================

def get_kpi():
    data = load_model()

    return {
        "mae": round(
            float(data["mae"]),
            6,
        ),
        "mse": round(
            float(data["mse"]),
            6,
        ),
        "rmse": round(
            float(data["rmse"]),
            6,
        ),
        "rating_count": int(
            data["rating_count"]
        ),
        "user_count": len(
            data["user_ids"]
        ),
        "movie_count": len(
            data["movie_ids"]
        ),
        "factors": int(
            data["factors"]
        ),
        "evaluation": data["evaluation"],
    }


# ==========================================
# 7. 고객별 추천 영화 TOP 5
# ==========================================

def get_recommendations(user_id: int):
    data = load_model()

    user_ids = data["user_ids"]
    movie_ids = data["movie_ids"]

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

    model = data["model"]

    # 모든 영화의 예측 평점 계산
    with torch.no_grad():
        user_tensor = torch.full(
            (len(movie_ids),),
            user_pos,
            dtype=torch.long,
        )

        movie_tensor = torch.arange(
            len(movie_ids),
            dtype=torch.long,
        )

        predicted = model(
            user_tensor,
            movie_tensor,
        ).clamp(
            1.0,
            5.0,
        ).numpy()

    # 이미 본 영화 제외
    seen_ids = repository.get_seen_movie_ids(
        user_id
    )

    unseen_mask = ~np.isin(
        movie_ids,
        list(seen_ids),
    )

    candidate_indices = np.flatnonzero(
        unseen_mask
    )

    if len(candidate_indices) == 0:
        return {
            "user_id": user_id,
            "recommendations": [],
        }

    candidate_scores = predicted[
        candidate_indices
    ]

    top_count = min(
        5,
        len(candidate_indices),
    )

    # 예측 평점 내림차순
    order = np.lexsort((
        movie_ids[candidate_indices],
        -candidate_scores,
    ))

    top_indices = candidate_indices[
        order[:top_count]
    ]

    selected_movie_ids = [
        int(movie_ids[idx])
        for idx in top_indices
    ]

    details = repository.get_movie_details(
        selected_movie_ids
    )

    recommendations = []

    for rank, idx in enumerate(
        top_indices,
        start=1,
    ):
        movie_id = int(
            movie_ids[idx]
        )

        info = details.get(
            movie_id,
            {},
        )

        recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": info.get(
                "title",
                f"영화 {movie_id}",
            ),
            "genres": info.get(
                "genres",
                "",
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
# 8. CLI 실행
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="MF 딥러닝 영화 추천 모델"
    )

    parser.add_argument(
        "command",
        choices=["train"],
        help="MF 모델 학습",
    )

    args = parser.parse_args()

    if args.command == "train":
        train_model()


if __name__ == "__main__":
    main()
