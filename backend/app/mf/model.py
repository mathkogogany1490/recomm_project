
import torch
from torch import nn


class MatrixFactorization(nn.Module):
    def __init__(
        self,
        num_users: int,
        num_movies: int,
        factors: int = 30,
    ):
        super().__init__()

        self.user_embedding = nn.Embedding(
            num_users,
            factors,
        )

        self.movie_embedding = nn.Embedding(
            num_movies,
            factors,
        )

        self.user_bias = nn.Embedding(num_users, 1)
        self.movie_bias = nn.Embedding(num_movies, 1)

        self.global_bias = nn.Parameter(torch.zeros(1))

        nn.init.normal_(
            self.user_embedding.weight,
            std=0.05,
        )
        nn.init.normal_(
            self.movie_embedding.weight,
            std=0.05,
        )

        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.movie_bias.weight)

    def forward(self, user_ids, movie_ids):
        user_vector = self.user_embedding(user_ids)
        movie_vector = self.movie_embedding(movie_ids)

        dot = (user_vector * movie_vector).sum(dim=1)

        user_bias = self.user_bias(user_ids).squeeze(-1)
        movie_bias = self.movie_bias(movie_ids).squeeze(-1)

        return (
            dot
            + user_bias
            + movie_bias
            + self.global_bias
        )
