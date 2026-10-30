
import argparse
import json
import logging
import platform
import random
import sys
import time
import traceback

from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from tqdm import tqdm

from app.transformer.repository import (
    get_counts,
    get_movie_ids,
    iter_user_histories,
)


# ==========================================
# 1. 기본 설정
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

CHECKPOINT_DIR = (
    BASE_DIR / "checkpoint" / "transformer_model"
)

CHECKPOINT_PATH = (
    CHECKPOINT_DIR / "training_v2.pt"
)

STATUS_PATH = (
    CHECKPOINT_DIR / "training_status.json"
)

EMBED_DIM = 30
MAX_SEQ_LEN = 30
NUM_HEADS = 3
NUM_LAYERS = 2
DROPOUT = 0.1

DEFAULT_EPOCHS = 10
DEFAULT_BATCH_SIZE = 64
DEFAULT_LR = 0.001
DB_BATCH_SIZE = 1000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("transformer")


# ==========================================
# 2. 화면 출력
# ==========================================

def show(message=""):
    tqdm.write(
        str(message),
        file=sys.stderr,
    )


def show_step(number, message):
    show(
        f"\n[{number}] {message}"
    )


def elapsed_text(seconds):
    seconds = int(seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{seconds:02d}"
    )


# ==========================================
# 3. 학습 상태 JSON 저장
# ==========================================

def save_status(**kwargs):
    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        **kwargs,
    }

    temp_path = STATUS_PATH.with_suffix(".tmp")

    temp_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp_path.replace(STATUS_PATH)


# ==========================================
# 4. CPU / GPU 확인
# ==========================================

def get_device(force_cpu=False):
    show_step(
        "1/8",
        "CPU / GPU 사용 가능 여부 확인"
    )

    show(f"운영체제: {platform.platform()}")
    show(f"Python: {sys.version.split()[0]}")
    show(f"PyTorch: {torch.__version__}")

    cuda_available = torch.cuda.is_available()

    mps_built = (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_built()
    )

    mps_available = (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    )

    show(
        f"CUDA GPU 사용 가능: {cuda_available}"
    )

    show(
        f"Apple MPS 지원 빌드: {mps_built}"
    )

    show(
        f"Apple MPS 사용 가능: {mps_available}"
    )

    if force_cpu:
        device = torch.device("cpu")

    elif cuda_available:
        device = torch.device("cuda")

    elif mps_available:
        device = torch.device("mps")

    else:
        device = torch.device("cpu")

    if device.type == "cuda":
        show(
            "CUDA GPU 이름: "
            + torch.cuda.get_device_name(0)
        )

    elif device.type == "mps":
        show(
            "Apple Silicon GPU 가속 사용: MPS"
        )

    else:
        show(
            "GPU 가속 미사용: CPU 학습"
        )

    show(
        f"실제 학습 장치: {device}"
    )

    return device


# ==========================================
# 5. Transformer 모델
# ==========================================

class MovieTransformer(nn.Module):
    def __init__(
        self,
        num_movies,
        embedding_dim=EMBED_DIM,
        max_seq_len=MAX_SEQ_LEN,
    ):
        super().__init__()

        self.max_seq_len = max_seq_len

        self.movie_embedding = nn.Embedding(
            num_movies + 1,
            embedding_dim,
            padding_idx=0,
        )

        self.position_embedding = nn.Embedding(
            max_seq_len,
            embedding_dim,
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim,
            nhead=NUM_HEADS,
            dim_feedforward=embedding_dim * 4,
            dropout=DROPOUT,
            batch_first=True,
        )

        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=NUM_LAYERS,
            enable_nested_tensor=False,
        )

        self.output = nn.Linear(
            embedding_dim,
            num_movies + 1,
        )

    def forward(self, sequences):
        batch_size, seq_len = sequences.shape

        positions = torch.arange(
            seq_len,
            device=sequences.device,
        ).unsqueeze(0)

        x = (
            self.movie_embedding(sequences)
            + self.position_embedding(positions)
        )

        causal_mask = torch.triu(
            torch.ones(
                seq_len,
                seq_len,
                device=sequences.device,
                dtype=torch.bool,
            ),
            diagonal=1,
        )

        padding_mask = sequences.eq(0)

        encoded = self.encoder(
            x,
            mask=causal_mask,
            src_key_padding_mask=padding_mask,
        )

        lengths = (
            (~padding_mask).sum(dim=1) - 1
        ).clamp(min=0)

        last_hidden = encoded[
            torch.arange(
                batch_size,
                device=sequences.device,
            ),
            lengths,
        ]

        return self.output(last_hidden)


# ==========================================
# 6. 학습 데이터 생성
# ==========================================

def make_sample(history, movie_to_idx):
    """
    고객의 마지막 영화를 정답으로 사용합니다.

    이전 영화들 -> 다음 영화 예측

    반환:
        (sequence, target)
    """

    movie_indices = [
        movie_to_idx[movie_id]
        for movie_id, rating in history
        if movie_id in movie_to_idx
    ]

    if len(movie_indices) < 2:
        return None

    target = movie_indices[-1]

    sequence = movie_indices[
        -(MAX_SEQ_LEN + 1):-1
    ]

    sequence = sequence[-MAX_SEQ_LEN:]

    return sequence, target


def make_batch(samples, device):
    sequences, targets = zip(*samples)

    max_len = max(
        len(sequence)
        for sequence in sequences
    )

    x = torch.zeros(
        len(samples),
        max_len,
        dtype=torch.long,
    )

    for i, sequence in enumerate(sequences):
        x[i, :len(sequence)] = torch.tensor(
            sequence,
            dtype=torch.long,
        )

    y = torch.tensor(
        targets,
        dtype=torch.long,
    )

    return x.to(device), y.to(device)


# ==========================================
# 7. 배치 학습
# ==========================================

def train_batch(
    model,
    optimizer,
    samples,
    device,
):
    x, y = make_batch(samples, device)

    model.train()

    optimizer.zero_grad(
        set_to_none=True
    )

    logits = model(x)

    loss = F.cross_entropy(
        logits,
        y,
    )

    loss.backward()

    torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        max_norm=1.0,
    )

    optimizer.step()

    predictions = logits.argmax(dim=1)

    correct = (
        predictions == y
    ).sum().item()

    return (
        float(loss.item()),
        int(correct),
        len(samples),
    )


# ==========================================
# 8. 체크포인트 저장
# ==========================================

def save_checkpoint(
    model,
    optimizer,
    epoch,
    movie_ids,
    loss,
    accuracy,
):
    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "movie_ids": movie_ids,
        "embedding_dim": EMBED_DIM,
        "max_seq_len": MAX_SEQ_LEN,
        "loss": loss,
        "accuracy": accuracy,
    }

    temp_path = CHECKPOINT_PATH.with_suffix(
        ".tmp"
    )

    torch.save(
        checkpoint,
        temp_path,
    )

    temp_path.replace(
        CHECKPOINT_PATH
    )

    show(
        f"체크포인트 저장 완료: {CHECKPOINT_PATH}"
    )


# ==========================================
# 9. Transformer 학습
# ==========================================

def train_model(
    epochs=DEFAULT_EPOCHS,
    batch_size=DEFAULT_BATCH_SIZE,
    learning_rate=DEFAULT_LR,
    resume=False,
    force_cpu=False,
):
    total_start = time.time()

    random.seed(42)
    torch.manual_seed(42)

    show("=" * 65)
    show("TRANSFORMER MOVIE RECOMMENDATION TRAINING")
    show("=" * 65)

    show(
        f"학습 시작: "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    show(
        f"Epoch: {epochs}"
    )

    show(
        f"Batch Size: {batch_size}"
    )

    show(
        f"Embedding Dimension: {EMBED_DIM}"
    )

    show(
        f"Sequence Length: {MAX_SEQ_LEN}"
    )

    show(
        f"Learning Rate: {learning_rate}"
    )

    save_status(
        state="initializing",
        epoch=0,
        total_epochs=epochs,
        message="학습 환경 확인 중",
    )

    # --------------------------------------
    # STEP 1. GPU 확인
    # --------------------------------------

    device = get_device(force_cpu)

    # --------------------------------------
    # STEP 2. PostgreSQL 데이터 건수
    # --------------------------------------

    show_step(
        "2/8",
        "PostgreSQL 데이터 건수 조회 중..."
    )

    query_start = time.time()

    counts = get_counts()

    show(
        f"평점 건수: {counts['rating_count']:,}"
    )

    show(
        f"고객 수: {counts['user_count']:,}"
    )

    show(
        f"영화 수: {counts['movie_count']:,}"
    )

    show(
        "조회 소요 시간: "
        + elapsed_text(
            time.time() - query_start
        )
    )

    if counts["user_count"] == 0:
        raise RuntimeError(
            "학습할 고객 평점 데이터가 없습니다."
        )

    # --------------------------------------
    # STEP 3. 영화 ID 조회
    # --------------------------------------

    show_step(
        "3/8",
        "영화 ID 목록 조회 중..."
    )

    movie_ids = get_movie_ids()

    if not movie_ids:
        raise RuntimeError(
            "영화 데이터가 없습니다."
        )

    movie_to_idx = {
        movie_id: idx + 1
        for idx, movie_id in enumerate(movie_ids)
    }

    show(
        f"영화 ID 로딩 완료: {len(movie_ids):,}개"
    )

    # --------------------------------------
    # STEP 4. 모델 초기화
    # --------------------------------------

    show_step(
        "4/8",
        "Transformer 모델 생성 중..."
    )

    model = MovieTransformer(
        num_movies=len(movie_ids),
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
    )

    parameter_count = sum(
        parameter.numel()
        for parameter in model.parameters()
    )

    show(
        f"모델 파라미터 수: {parameter_count:,}"
    )

    show(
        f"모델 실행 장치: "
        f"{next(model.parameters()).device}"
    )

    start_epoch = 1

    # --------------------------------------
    # STEP 5. 체크포인트 복원
    # --------------------------------------

    show_step(
        "5/8",
        "체크포인트 확인 중..."
    )

    if resume:
        if not CHECKPOINT_PATH.exists():
            raise FileNotFoundError(
                f"체크포인트가 없습니다: "
                f"{CHECKPOINT_PATH}"
            )

        checkpoint = torch.load(
            CHECKPOINT_PATH,
            map_location=device,
            weights_only=True,
        )

        if checkpoint["movie_ids"] != movie_ids:
            raise RuntimeError(
                "체크포인트 영화 목록과 "
                "현재 DB 영화 목록이 다릅니다."
            )

        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        optimizer.load_state_dict(
            checkpoint["optimizer_state_dict"]
        )

        start_epoch = (
            int(checkpoint["epoch"]) + 1
        )

        show(
            f"체크포인트 복원 완료: "
            f"Epoch {start_epoch}부터 재개"
        )

    else:
        show(
            "새로운 모델 학습을 시작합니다."
        )

    if start_epoch > epochs:
        show(
            "이미 요청한 Epoch까지 학습되어 있습니다."
        )
        return

    # --------------------------------------
    # STEP 6. 학습 시작
    # --------------------------------------

    show_step(
        "6/8",
        "Transformer 학습 시작"
    )

    show(
        f"학습 장치: {device}"
    )

    show(
        "학습 지표: Loss / Accuracy / Error Rate"
    )

    for epoch in range(
        start_epoch,
        epochs + 1,
    ):
        epoch_start = time.time()

        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        batch_count = 0

        samples = []

        show("\n" + "-" * 65)
        show(
            f"Epoch {epoch}/{epochs} 시작"
        )
        show("-" * 65)

        save_status(
            state="training",
            epoch=epoch,
            total_epochs=epochs,
            device=str(device),
            message="고객 평점 이력 조회 및 모델 학습 중",
            processed_users=0,
            total_users=counts["user_count"],
        )

        progress = tqdm(
            iter_user_histories(
                batch_size=DB_BATCH_SIZE
            ),
            total=counts["user_count"],
            desc=f"Epoch {epoch}/{epochs}",
            unit="user",
            dynamic_ncols=True,
            mininterval=1.0,
            file=sys.stderr,
        )

        for user_id, history in progress:
            sample = make_sample(
                history,
                movie_to_idx,
            )

            if sample is not None:
                samples.append(sample)

            if len(samples) >= batch_size:
                loss, correct, count = train_batch(
                    model,
                    optimizer,
                    samples,
                    device,
                )

                total_loss += loss * count
                total_correct += correct
                total_samples += count
                batch_count += 1

                samples.clear()

                avg_loss = (
                    total_loss / total_samples
                )

                accuracy = (
                    total_correct
                    / total_samples
                    * 100
                )

                error_rate = (
                    100 - accuracy
                )

                progress.set_postfix({
                    "loss": f"{avg_loss:.4f}",
                    "acc": f"{accuracy:.2f}%",
                    "error": f"{error_rate:.2f}%",
                    "batch": batch_count,
                    "device": str(device),
                })

                if batch_count % 20 == 0:
                    save_status(
                        state="training",
                        epoch=epoch,
                        total_epochs=epochs,
                        device=str(device),
                        processed_users=progress.n,
                        total_users=counts["user_count"],
                        loss=round(avg_loss, 6),
                        accuracy=round(accuracy, 3),
                        error_rate=round(
                            error_rate, 3
                        ),
                        batches=batch_count,
                        elapsed_seconds=round(
                            time.time() - epoch_start,
                            2,
                        ),
                    )

        progress.close()

        # 마지막 배치
        if samples:
            loss, correct, count = train_batch(
                model,
                optimizer,
                samples,
                device,
            )

            total_loss += loss * count
            total_correct += correct
            total_samples += count
            batch_count += 1

        if total_samples == 0:
            raise RuntimeError(
                "유효한 학습 데이터가 없습니다."
            )

        avg_loss = (
            total_loss / total_samples
        )

        accuracy = (
            total_correct / total_samples
            * 100
        )

        error_rate = 100 - accuracy

        epoch_seconds = (
            time.time() - epoch_start
        )

        show("\nEpoch 학습 결과")
        show(
            f"Epoch: {epoch}/{epochs}"
        )
        show(
            f"Loss: {avg_loss:.6f}"
        )
        show(
            f"Accuracy: {accuracy:.2f}%"
        )
        show(
            f"Error Rate: {error_rate:.2f}%"
        )
        show(
            f"학습 샘플: {total_samples:,}"
        )
        show(
            f"학습 배치: {batch_count:,}"
        )
        show(
            f"소요 시간: "
            f"{elapsed_text(epoch_seconds)}"
        )

        save_checkpoint(
            model=model,
            optimizer=optimizer,
            epoch=epoch,
            movie_ids=movie_ids,
            loss=avg_loss,
            accuracy=accuracy,
        )

        save_status(
            state="epoch_completed",
            epoch=epoch,
            total_epochs=epochs,
            device=str(device),
            processed_users=counts["user_count"],
            total_users=counts["user_count"],
            loss=round(avg_loss, 6),
            accuracy=round(accuracy, 3),
            error_rate=round(error_rate, 3),
            batches=batch_count,
            epoch_seconds=round(
                epoch_seconds, 2
            ),
        )

    # --------------------------------------
    # STEP 7. 학습 완료
    # --------------------------------------

    show_step(
        "7/8",
        "전체 학습 완료"
    )

    total_elapsed = (
        time.time() - total_start
    )

    show(
        f"총 소요 시간: "
        f"{elapsed_text(total_elapsed)}"
    )

    show(
        f"최종 Loss: {avg_loss:.6f}"
    )

    show(
        f"최종 Accuracy: {accuracy:.2f}%"
    )

    show(
        f"최종 Error Rate: {error_rate:.2f}%"
    )

    # --------------------------------------
    # STEP 8. 종료 상태 저장
    # --------------------------------------

    show_step(
        "8/8",
        "학습 결과 저장 완료"
    )

    save_status(
        state="completed",
        epoch=epochs,
        total_epochs=epochs,
        device=str(device),
        loss=round(avg_loss, 6),
        accuracy=round(accuracy, 3),
        error_rate=round(error_rate, 3),
        total_seconds=round(
            total_elapsed, 2
        ),
    )

    show(
        f"모델 파일: {CHECKPOINT_PATH}"
    )

    show(
        f"상태 파일: {STATUS_PATH}"
    )

    show("=" * 65)
    show("TRANSFORMER TRAINING FINISHED")
    show("=" * 65)


# ==========================================
# 10. 실행 / 오류 처리
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="Transformer 영화 추천 모델 학습"
    )

    parser.add_argument(
        "mode",
        choices=["train"],
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=DEFAULT_EPOCHS,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )

    parser.add_argument(
        "--lr",
        type=float,
        default=DEFAULT_LR,
    )

    parser.add_argument(
        "--resume",
        action="store_true",
    )

    parser.add_argument(
        "--cpu",
        action="store_true",
        help="GPU를 사용하지 않고 CPU로 학습",
    )

    args = parser.parse_args()

    if args.epochs < 1:
        parser.error(
            "epochs는 1 이상이어야 합니다."
        )

    if args.batch_size < 1:
        parser.error(
            "batch-size는 1 이상이어야 합니다."
        )

    if args.lr <= 0:
        parser.error(
            "lr은 0보다 커야 합니다."
        )

    try:
        train_model(
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            resume=args.resume,
            force_cpu=args.cpu,
        )

    except KeyboardInterrupt:
        show(
            "\n[중단] 사용자가 학습을 중단했습니다."
        )

        save_status(
            state="interrupted",
            error="KeyboardInterrupt",
        )

        raise SystemExit(130)

    except Exception as exc:
        show("\n" + "=" * 65)
        show("[ERROR] Transformer 학습 실패")
        show("=" * 65)

        show(
            f"오류 종류: {type(exc).__name__}"
        )

        show(
            f"오류 내용: {exc}"
        )

        show("\n상세 오류 위치:")

        traceback.print_exc(
            file=sys.stderr
        )

        save_status(
            state="failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
