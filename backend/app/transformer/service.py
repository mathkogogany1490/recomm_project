
import argparse
import os
import tempfile

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

from . import repository
from .model import MovieTransformer


MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "checkpoint"
    / "transformer_model"
    / "transformer_model.pt"
)

MAX_LEN = 30
D_MODEL = 64
NHEAD = 4
NUM_LAYERS = 2
BATCH_SIZE = 256
EPOCHS = 10
LEARNING_RATE = 0.001
SEED = 42


# ==========================================
# 1. 장치 자동 선택
# ==========================================

def get_device():
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(
            "학습 장치: CUDA GPU "
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
# 2. 시퀀스 데이터 변환
# ==========================================

def rating_token(rating):
    # 0.5 단위 평점 -> 1~10
    return max(
        1,
        min(10, int(round(float(rating) * 2)))
    )


def make_sample(history, target_index, movie_to_idx):
    """
    target_index 이전의 영화/평점만 입력.
    현재 시점 영화의 평점을 예측.
    """
    context = history[
        max(0, target_index - MAX_LEN):target_index
    ]

    movie_seq = [
        movie_to_idx[movie_id]
        for movie_id, _ in context
    ]

    rating_seq = [
        rating_token(rating)
        for _, rating in context
    ]

    # 오른쪽 패딩
    padding = MAX_LEN - len(movie_seq)

    movie_seq += [0] * padding
    rating_seq += [0] * padding

    target_movie, target_rating = history[
        target_index
    ]

    return (
        movie_seq,
        rating_seq,
        movie_to_idx[target_movie],
        float(target_rating),
    )


def make_tensors(samples, device):
    movie_seqs = torch.tensor(
        [row[0] for row in samples],
        dtype=torch.long,
        device=device,
    )

    rating_seqs = torch.tensor(
        [row[1] for row in samples],
        dtype=torch.long,
        device=device,
    )

    targets = torch.tensor(
        [row[2] for row in samples],
        dtype=torch.long,
        device=device,
    )

    actuals = torch.tensor(
        [row[3] for row in samples],
        dtype=torch.float32,
        device=device,
    )

    return movie_seqs, rating_seqs, targets, actuals


# ==========================================
# 3. 한 배치 학습
# ==========================================

def train_batch(
    model,
    optimizer,
    criterion,
    samples,
    device,
):
    movie_seqs, rating_seqs, targets, actuals = (
        make_tensors(samples, device)
    )

    optimizer.zero_grad()

    predicted = model(
        movie_seqs,
        rating_seqs,
        targets,
    )

    loss = criterion(predicted, actuals)

    loss.backward()
    optimizer.step()

    return float(loss.item()) * len(samples)


# ==========================================
# 4. 검증
# ==========================================

def evaluate_model(model, movie_to_idx, device):
    model.eval()

    absolute_sum = 0.0
    squared_sum = 0.0
    count = 0
    samples = []

    def evaluate_batch(batch):
        nonlocal absolute_sum, squared_sum, count

        tensors = make_tensors(batch, device)
        movie_seqs, rating_seqs, targets, actuals = tensors

        with torch.no_grad():
            predicted = model(
                movie_seqs,
                rating_seqs,
                targets,
            ).clamp(1.0, 5.0)

            # MPS에서 float64를 사용하지 않음
            # CPU 이동 후 float64로 누적
            errors = (
                (predicted - actuals)
                .detach()
                .cpu()
                .double()
            )

            absolute_sum += errors.abs().sum().item()
            squared_sum += errors.square().sum().item()
            count += len(batch)

    for _, history in tqdm(
        repository.iter_user_histories(),
        desc="검증",
        unit="user",
    ):
        if len(history) < 3:
            continue

        sample = make_sample(
            history,
            len(history) - 1,
            movie_to_idx,
        )

        samples.append(sample)

        if len(samples) >= BATCH_SIZE:
            evaluate_batch(samples)
            samples.clear()

    if samples:
        evaluate_batch(samples)

    if count == 0:
        raise ValueError(
            "검증할 고객 이력이 없습니다."
        )

    mae = absolute_sum / count
    mse = squared_sum / count
    rmse = float(np.sqrt(mse))

    return mae, mse, rmse, count


# ==========================================
# 5. Transformer 학습
# ==========================================

def train_model():
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    print("\n========== Transformer 학습 ==========")

    counts = repository.get_counts()

    if counts["rating_count"] == 0:
        raise ValueError(
            "PostgreSQL에 평점 데이터가 없습니다. "
            "먼저 import-data를 실행하세요."
        )

    movie_ids = repository.get_movie_ids()

    if not movie_ids:
        raise ValueError("영화 데이터가 없습니다.")

    # 0은 패딩, 실제 영화는 1부터 시작
    movie_to_idx = {
        movie_id: idx + 1
        for idx, movie_id in enumerate(movie_ids)
    }

    print(f"고객: {counts['user_count']:,}명")
    print(f"영화: {len(movie_ids):,}편")
    print(f"평점: {counts['rating_count']:,}건")

    device = get_device()

    model = MovieTransformer(
        num_movies=len(movie_ids),
        d_model=D_MODEL,
        nhead=NHEAD,
        num_layers=NUM_LAYERS,
        max_len=MAX_LEN,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=1e-5,
    )

    criterion = torch.nn.MSELoss()

    history_metrics = []

    for epoch in range(EPOCHS):
        model.train()

        samples = []
        loss_sum = 0.0
        train_count = 0

        progress = tqdm(
            repository.iter_user_histories(),
            total=counts["user_count"],
            desc=f"Epoch {epoch + 1}/{EPOCHS}",
            unit="user",
        )

        for _, history in progress:
            if len(history) < 3:
                continue

            # 마지막 평점은 검증용으로 제외
            for target_index in range(
                1, len(history) - 1
            ):
                samples.append(
                    make_sample(
                        history,
                        target_index,
                        movie_to_idx,
                    )
                )

                if len(samples) >= BATCH_SIZE:
                    batch_loss = train_batch(
                        model,
                        optimizer,
                        criterion,
                        samples,
                        device,
                    )

                    loss_sum += batch_loss
                    train_count += len(samples)
                    samples.clear()

                    progress.set_postfix(
                        train_mse=(
                            f"{loss_sum / train_count:.5f}"
                        )
                    )

        if samples:
            batch_loss = train_batch(
                model,
                optimizer,
                criterion,
                samples,
                device,
            )

            loss_sum += batch_loss
            train_count += len(samples)
            samples.clear()

        if train_count == 0:
            raise ValueError(
                "학습할 시퀀스가 없습니다. "
                "평점이 3개 이상인 고객이 필요합니다."
            )

        train_mse = loss_sum / train_count

        mae, mse, rmse, validation_count = (
            evaluate_model(
                model,
                movie_to_idx,
                device,
            )
        )

        history_metrics.append({
            "epoch": epoch + 1,
            "train_mse": float(train_mse),
            "val_mse": float(mse),
            "val_mae": float(mae),
            "val_rmse": float(rmse),
        })

        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Train MSE={train_mse:.6f} | "
            f"Val MSE={mse:.6f} | "
            f"Val MAE={mae:.6f} | "
            f"Val RMSE={rmse:.6f}"
        )

    # ======================================
    # 6. 체크포인트 저장
    # ======================================

    model.to("cpu")

    checkpoint = {
        "state_dict": model.state_dict(),
        "movie_ids": torch.tensor(
            movie_ids,
            dtype=torch.long,
        ),
        "max_len": MAX_LEN,
        "d_model": D_MODEL,
        "nhead": NHEAD,
        "num_layers": NUM_LAYERS,
        "epochs": EPOCHS,
        "mse": float(mse),
        "mae": float(mae),
        "rmse": float(rmse),
        "validation_count": int(validation_count),
        "counts": counts,
        "history": history_metrics,
        "evaluation": "last_rating_per_user",
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
        torch.save(checkpoint, temp_path)
        os.replace(temp_path, MODEL_PATH)
    finally:
        temp_path.unlink(missing_ok=True)

    load_model.cache_clear()

    print("\n========== 학습 완료 ==========")
    print(f"MSE  : {mse:.6f}")
    print(f"MAE  : {mae:.6f}")
    print(f"RMSE : {rmse:.6f}")
    print(f"저장 : {MODEL_PATH}")

    return checkpoint


# ==========================================
# 7. 체크포인트 로드
# ==========================================

@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Transformer 모델이 없습니다. "
            "먼저 학습하세요."
        )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )

    movie_ids = checkpoint["movie_ids"].tolist()

    model = MovieTransformer(
        num_movies=len(movie_ids),
        d_model=checkpoint["d_model"],
        nhead=checkpoint["nhead"],
        num_layers=checkpoint["num_layers"],
        max_len=checkpoint["max_len"],
    )

    model.load_state_dict(
        checkpoint["state_dict"]
    )
    model.eval()

    return {
        "model": model,
        "movie_ids": movie_ids,
        "movie_to_idx": {
            movie_id: idx + 1
            for idx, movie_id in enumerate(movie_ids)
        },
        "checkpoint": checkpoint,
    }


# ==========================================
# 8. KPI
# ==========================================

def get_kpi():
    data = load_model()
    checkpoint = data["checkpoint"]
    counts = checkpoint["counts"]

    return {
        "mse": round(float(checkpoint["mse"]), 6),
        "mae": round(float(checkpoint["mae"]), 6),
        "rmse": round(float(checkpoint["rmse"]), 6),
        "rating_count": counts["rating_count"],
        "user_count": counts["user_count"],
        "movie_count": counts["movie_count"],
        "epochs": checkpoint["epochs"],
        "evaluation": checkpoint["evaluation"],
    }


# ==========================================
# 9. 추천 영화 TOP 5
# ==========================================

def get_recommendations(user_id):
    data = load_model()

    model = data["model"]
    movie_ids = data["movie_ids"]
    movie_to_idx = data["movie_to_idx"]

    history = repository.get_user_history(
        user_id
    )

    if not history:
        raise ValueError(
            "평점 이력이 없는 고객입니다."
        )

    # 전체 이력에서 본 영화 제외
    seen_movie_ids = {
        movie_id
        for movie_id, _ in history
    }

    context = history[-MAX_LEN:]

    movie_seq = [
        movie_to_idx[movie_id]
        for movie_id, _ in context
    ]

    rating_seq = [
        rating_token(rating)
        for _, rating in context
    ]

    padding = MAX_LEN - len(movie_seq)

    movie_seq += [0] * padding
    rating_seq += [0] * padding

    movie_tensor = torch.tensor(
        [movie_seq],
        dtype=torch.long,
    )

    rating_tensor = torch.tensor(
        [rating_seq],
        dtype=torch.long,
    )

    candidates = [
        movie_id
        for movie_id in movie_ids
        if movie_id not in seen_movie_ids
    ]

    if not candidates:
        return {
            "user_id": user_id,
            "recommendations": [],
        }

    # 이력은 한 번만 인코딩
    with torch.no_grad():
        context_vector = model.encode(
            movie_tensor,
            rating_tensor,
        )

        scored = []

        for start in range(
            0, len(candidates), 2048
        ):
            chunk = candidates[start:start + 2048]

            indices = torch.tensor(
                [
                    movie_to_idx[movie_id]
                    for movie_id in chunk
                ],
                dtype=torch.long,
            ).unsqueeze(0)

            scores = model.score(
                context_vector,
                indices,
            ).clamp(1.0, 5.0)

            for movie_id, score in zip(
                chunk,
                scores.squeeze(0).tolist(),
            ):
                scored.append((
                    movie_id,
                    float(score),
                ))

    scored.sort(
        key=lambda item: (-item[1], item[0])
    )

    top_five = scored[:5]

    details = repository.get_movie_details(
        [movie_id for movie_id, _ in top_five]
    )

    recommendations = []

    for rank, (movie_id, score) in enumerate(
        top_five,
        start=1,
    ):
        movie = details.get(movie_id, {})

        recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": movie.get(
                "title",
                f"영화 {movie_id}",
            ),
            "genres": movie.get("genres", ""),
            "predicted_rating": round(score, 4),
        })

    return {
        "user_id": user_id,
        "recommendations": recommendations,
    }


# ==========================================
# 10. CLI
# ==========================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "command",
        choices=["import-data", "train"],
    )

    args = parser.parse_args()

    if args.command == "import-data":
        repository.create_tables()
        repository.import_movies()
        repository.import_ratings()

    elif args.command == "train":
        train_model()


if __name__ == "__main__":
    main()
