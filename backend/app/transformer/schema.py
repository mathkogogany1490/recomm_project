
from pydantic import BaseModel, Field


class TransformerKpiResponse(BaseModel):
    mse: float
    mae: float
    rmse: float
    rating_count: int
    user_count: int
    movie_count: int
    epochs: int
    evaluation: str


class TransformerRecommendationItem(BaseModel):
    rank: int = Field(ge=1, le=5)
    movie_id: int
    title: str
    genres: str
    predicted_rating: float


class TransformerRecommendationsResponse(BaseModel):
    user_id: int
    recommendations: list[TransformerRecommendationItem]
