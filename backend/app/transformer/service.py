import argparse
import os
import tempfile

from functools import lru_cache
from pathlib import Path

import numpy as np
import torch

from tqdm import tqdm

from app.genres import to_korean_genres
from app.transformer.repository import (
    get_counts,
    get_movie_details,
    get_movie_ids,
    get_user_history,
    iter_user_histories,
)
from .model import MovieTransformer


BASE_DIR = Path(__file__).resolve().parents[2]

CHECKPOINT_DIR = (
    BASE_DIR / "checkpoint" / "transformer_model"
)

CHECKPOINT_PATH = (
    CHECKPOINT_DIR / "training_v2.pt"
)

D_MODEL = 64
NHEAD = 4
NUM_LAYERS = 2
MAX_LEN = 30
DROPOUT = 0.1

EPOCHS = 10
BATCH_SIZE = 256
LEARNING_RATE = 0.001
WEIGHT_DECAY = 1e-5
VALIDATION_RATIO = 0.1
SEED = 42
DB_BATCH_SIZE = 1000

EVALUATION = "관측 평점의 뒤 10% 검증"


def get_device():
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(
            "학습 장치: CUDA GPU "
            f"({torch.cuda.get_device_name(0)})"
        )
        return device

    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        print("학습 장치: Apple MPS GPU")
        return torch.device("mps")

    print("학습 장치: CPU")
    return torch.device("cpu")


def rating_index(rating):
    index = int(round(float(rating) * 2))
    return min(10, max(1, index))


def iter_rating_samples(history, movie_to_idx, train):
    indexed = []

    for movie_id, rating in history:
        index = movie_to_idx.get(int(movie_id))

        if index is None:
            continue

        indexed.append((index, float(rating)))

    count = len(indexed)

    if count < 2:
        return

    val_count = max(
        1,
        int(round(count * VALIDATION_RATIO)),
    )
    val_count = min(val_count, count - 1)
    split = count - val_count

    positions = (
        range(1, split)
        if train
        else range(split, count)
    )

    for target_pos in positions:
        start = max(0, target_pos - MAX_LEN)
        past = indexed[start:target_pos]

        if not past:
            continue

        yield (
            [movie for movie, _rating in past],
            [
                rating_index(rating)
                for _movie, rating in past
            ],
            indexed[target_pos][0],
            indexed[target_pos][1],
        )


def collate(batch, device):
    movies, ratings, candidates, targets = zip(*batch)
    width = max(len(movie) for movie in movies)
    size = len(batch)

    movie_seq = torch.zeros(
        size,
        width,
        dtype=torch.long,
    )
    rating_seq = torch.zeros(
        size,
        width,
        dtype=torch.long,
    )

    for row, (movie, rating) in enumerate(
        zip(movies, ratings)
    ):
        movie_seq[row, :len(movie)] = torch.tensor(
            movie,
            dtype=torch.long,
        )
        rating_seq[row, :len(rating)] = torch.tensor(
            rating,
            dtype=torch.long,
        )

    candidate = torch.tensor(
        candidates,
        dtype=torch.long,
    )
    target = torch.tensor(
        targets,
        dtype=torch.float32,
    )

    return (
        movie_seq.to(device),
        rating_seq.to(device),
        candidate.to(device),
        target.to(device),
    )


def run_pass(
    model,
    movie_to_idx,
    device,
    optimizer,
    criterion,
    user_count,
    train,
):
    if train:
        model.train()
    else:
        model.eval()

    total_loss = 0.0
    absolute_sum = 0.0
    squared_sum = 0.0
    sample_count = 0
    batch = []

    def flush():
        nonlocal total_loss, absolute_sum, squared_sum, sample_count

        if not batch:
            return

        movie_seq, rating_seq, candidate, target = collate(
            batch,
            device,
        )

        if train:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(train):
            predicted = model(
                movie_seq,
                rating_seq,
                candidate,
            )
            loss = criterion(predicted, target)

            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    max_norm=1.0,
                )
                optimizer.step()

        clamped = (
            predicted.detach()
            .clamp(1.0, 5.0)
            .cpu()
            .double()
        )
        actual = target.detach().cpu().double()
        error = actual - clamped
        size = len(batch)

        total_loss += float(loss.item()) * size
        absolute_sum += float(error.abs().sum().item())
        squared_sum += float(error.square().sum().item())
        sample_count += size
        batch.clear()

    progress = tqdm(
        iter_user_histories(batch_size=DB_BATCH_SIZE),
        total=user_count,
        desc="학습" if train else "검증",
        unit="user",
    )

    for _user_id, history in progress:
        for sample in iter_rating_samples(
            history,
            movie_to_idx,
            train,
        ):
            batch.append(sample)

            if len(batch) >= BATCH_SIZE:
                flush()

        if sample_count:
            progress.set_postfix(
                mse=f"{total_loss / sample_count:.4f}"
            )

    progress.close()
    flush()

    if sample_count == 0:
        raise RuntimeError(
            "학습할 관측 평점이 없습니다."
            if train
            else "검증할 관측 평점이 없습니다."
        )

    mae = absolute_sum / sample_count
    mse = squared_sum / sample_count
    rmse = float(np.sqrt(mse))

    return (
        total_loss / sample_count,
        mae,
        mse,
        rmse,
        sample_count,
    )


def train_model():
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    print("\n========== Transformer 평점 학습 시작 ==========")

    counts = get_counts()
    movie_ids = get_movie_ids()

    if not movie_ids or counts["rating_count"] == 0:
        raise RuntimeError(
            "PostgreSQL에 학습할 평점 데이터가 없습니다."
        )

    movie_to_idx = {
        movie_id: index + 1
        for index, movie_id in enumerate(movie_ids)
    }

    print(f"고객 수: {counts['user_count']:,}명")
    print(f"영화 수: {counts['movie_count']:,}편")
    print(f"평점 수: {counts['rating_count']:,}건")

    device = get_device()

    model = MovieTransformer(
        num_movies=len(movie_ids),
        d_model=D_MODEL,
        nhead=NHEAD,
        num_layers=NUM_LAYERS,
        max_len=MAX_LEN,
        dropout=DROPOUT,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )
    criterion = torch.nn.MSELoss()

    mae = mse = rmse = 0.0

    for epoch in range(1, EPOCHS + 1):
        train_loss, train_mae, train_mse, train_rmse, train_count = (
            run_pass(
                model,
                movie_to_idx,
                device,
                optimizer,
                criterion,
                counts["user_count"],
                train=True,
            )
        )

        _val_loss, mae, mse, rmse, val_count = run_pass(
            model,
            movie_to_idx,
            device,
            optimizer,
            criterion,
            counts["user_count"],
            train=False,
        )

        print(
            f"Epoch {epoch}/{EPOCHS} | "
            f"Train MSE={train_mse:.6f} | "
            f"Train MAE={train_mae:.6f} | "
            f"Val MAE={mae:.6f} | "
            f"Val MSE={mse:.6f} | "
            f"Val RMSE={train_rmse and rmse:.6f} | "
            f"학습 {train_count:,} / 검증 {val_count:,}"
        )

        save_checkpoint(
            model=model,
            movie_ids=movie_ids,
            counts=counts,
            mae=mae,
            mse=mse,
            rmse=rmse,
            epoch=epoch,
        )

    load_model.cache_clear()

    print("\n========== Transformer 평점 학습 완료 ==========")
    print(f"MAE  : {mae:.6f}")
    print(f"MSE  : {mse:.6f}")
    print(f"RMSE : {rmse:.6f}")
    print(f"모델 저장: {CHECKPOINT_PATH}")

    return {
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
    }


def save_checkpoint(
    model,
    movie_ids,
    counts,
    mae,
    mse,
    rmse,
    epoch,
):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "state_dict": model.state_dict(),
        "movie_ids": movie_ids,
        "d_model": D_MODEL,
        "nhead": NHEAD,
        "num_layers": NUM_LAYERS,
        "max_len": MAX_LEN,
        "dropout": DROPOUT,
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
        "rating_count": int(counts["rating_count"]),
        "user_count": int(counts["user_count"]),
        "movie_count": int(counts["movie_count"]),
        "epoch": int(epoch),
        "evaluation": EVALUATION,
    }

    with tempfile.NamedTemporaryFile(
        dir=CHECKPOINT_DIR,
        suffix=".pt",
        delete=False,
    ) as temp:
        temp_path = Path(temp.name)

    try:
        torch.save(checkpoint, temp_path)
        os.replace(temp_path, CHECKPOINT_PATH)
    finally:
        temp_path.unlink(missing_ok=True)


@lru_cache(maxsize=1)
def load_model():
    if not CHECKPOINT_PATH.exists():
        raise FileNotFoundError(
            "Transformer 모델이 없습니다. 먼저 학습하세요."
        )

    checkpoint = torch.load(
        CHECKPOINT_PATH,
        map_location="cpu",
        weights_only=False,
    )

    if "state_dict" not in checkpoint or "mae" not in checkpoint:
        raise FileNotFoundError(
            "이전 다음-영화 분류 모델입니다. "
            "평점 예측으로 다시 학습하세요."
        )

    movie_ids = [
        int(movie_id)
        for movie_id in checkpoint["movie_ids"]
    ]

    model = MovieTransformer(
        num_movies=len(movie_ids),
        d_model=int(checkpoint.get("d_model", D_MODEL)),
        nhead=int(checkpoint.get("nhead", NHEAD)),
        num_layers=int(
            checkpoint.get("num_layers", NUM_LAYERS)
        ),
        max_len=int(checkpoint.get("max_len", MAX_LEN)),
        dropout=float(
            checkpoint.get("dropout", DROPOUT)
        ),
    )

    try:
        model.load_state_dict(checkpoint["state_dict"])
    except RuntimeError as exc:
        raise FileNotFoundError(
            "이전 다음-영화 분류 모델입니다. "
            "평점 예측으로 다시 학습하세요."
        ) from exc

    model.eval()

    return checkpoint, tuple(movie_ids), model


def get_kpi():
    checkpoint, _movie_ids, _model = load_model()
    counts = get_counts()

    return {
        "mae": round(float(checkpoint["mae"]), 6),
        "mse": round(float(checkpoint["mse"]), 6),
        "rmse": round(float(checkpoint["rmse"]), 6),
        "rating_count": counts["rating_count"],
        "user_count": counts["user_count"],
        "movie_count": counts["movie_count"],
        "epochs": int(checkpoint.get("epoch") or 0),
        "evaluation": checkpoint.get("evaluation")
        or EVALUATION,
    }


def get_recommendations(user_id: int):
    _checkpoint, movie_ids, model = load_model()
    movie_ids = list(movie_ids)
    movie_to_idx = {
        movie_id: index + 1
        for index, movie_id in enumerate(movie_ids)
    }

    history = get_user_history(user_id)
    indexed = []
    seen = set()

    for movie_id, rating in history:
        movie_id = int(movie_id)
        seen.add(movie_id)
        index = movie_to_idx.get(movie_id)

        if index is None:
            continue

        indexed.append((index, float(rating)))

    if not indexed:
        raise ValueError(
            "학습 데이터에 없는 고객 아이디입니다."
        )

    past = indexed[-MAX_LEN:]
    movie_seq = torch.tensor(
        [[movie for movie, _rating in past]],
        dtype=torch.long,
    )
    rating_seq = torch.tensor(
        [[rating_index(rating) for _movie, rating in past]],
        dtype=torch.long,
    )

    with torch.no_grad():
        context = model.encode(movie_seq, rating_seq)
        candidates = torch.arange(
            1,
            len(movie_ids) + 1,
            dtype=torch.long,
        ).view(1, -1)
        predicted = model.score(
            context,
            candidates,
        ).view(-1).clamp(1.0, 5.0).numpy()

    movie_id_array = np.asarray(movie_ids)
    unseen = np.array(
        [movie_id not in seen for movie_id in movie_ids]
    )
    positions = np.flatnonzero(unseen)

    if len(positions) == 0:
        return {
            "user_id": user_id,
            "recommendations": [],
        }

    order = np.lexsort((
        movie_id_array[positions],
        -predicted[positions],
    ))
    top_positions = positions[order[:5]]

    selected_ids = [
        int(movie_id_array[position])
        for position in top_positions
    ]
    details = get_movie_details(selected_ids)

    recommendations = []

    for rank, position in enumerate(top_positions, start=1):
        movie_id = int(movie_id_array[position])
        info = details.get(movie_id, {})
        recommendations.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": info.get("title") or f"영화 {movie_id}",
            "genres": to_korean_genres(
                info.get("genres") or ""
            ),
            "predicted_rating": round(
                float(predicted[position]),
                4,
            ),
        })

    return {
        "user_id": user_id,
        "recommendations": recommendations,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Transformer 평점 예측 모델 학습"
    )
    parser.add_argument(
        "command",
        choices=["train"],
    )
    args = parser.parse_args()

    if args.command == "train":
        train_model()


if __name__ == "__main__":
    main()