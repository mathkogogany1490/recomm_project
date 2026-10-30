
import torch
from torch import nn


class MovieTransformer(nn.Module):
    def __init__(
        self,
        num_movies,
        d_model=64,
        nhead=4,
        num_layers=2,
        max_len=30,
        dropout=0.1,
    ):
        super().__init__()

        self.max_len = max_len
        self.d_model = d_model

        # 0은 padding 전용
        self.movie_embedding = nn.Embedding(
            num_movies + 1, d_model, padding_idx=0
        )
        self.rating_embedding = nn.Embedding(11, d_model)
        self.position_embedding = nn.Embedding(max_len, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )

        self.encoder = nn.TransformerEncoder(
            layer,
            num_layers=num_layers,
            enable_nested_tensor=False,
        )

        self.regressor = nn.Sequential(
            nn.Linear(d_model * 2, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
        )

    def encode(self, movie_seq, rating_seq):
        batch_size, length = movie_seq.shape
        device = movie_seq.device

        positions = torch.arange(
            length, device=device
        ).unsqueeze(0)

        x = (
            self.movie_embedding(movie_seq)
            + self.rating_embedding(rating_seq)
            + self.position_embedding(positions)
        )

        padding_mask = movie_seq.eq(0)

        # 미래 시점 참조 금지
        causal_mask = torch.triu(
            torch.ones(
                length, length,
                dtype=torch.bool,
                device=device,
            ),
            diagonal=1,
        )

        encoded = self.encoder(
            x,
            mask=causal_mask,
            src_key_padding_mask=padding_mask,
        )

        last_index = (
            (~padding_mask).sum(dim=1) - 1
        ).clamp(min=0)

        batch_index = torch.arange(
            batch_size, device=device
        )

        return encoded[batch_index, last_index]

    def score(self, context, candidate_movies):
        movie_vector = self.movie_embedding(
            candidate_movies
        )

        if movie_vector.ndim == 3:
            context = context.unsqueeze(1).expand(
                -1, movie_vector.shape[1], -1
            )

        features = torch.cat(
            [context, movie_vector], dim=-1
        )

        return self.regressor(features).squeeze(-1)

    def forward(
        self,
        movie_seq,
        rating_seq,
        candidate_movies,
    ):
        context = self.encode(movie_seq, rating_seq)
        return self.score(context, candidate_movies)
