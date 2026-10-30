
from pydantic import BaseModel, Field


class SvdKpiResponse(BaseModel):
    mae: float
    mse: float
    rmse: float
    rating_count: int
    user_count: int
    movie_count: int
    factors: int
    evaluation: str


class SvdRecommendationItem(BaseModel):
    rank: int = Field(ge=1, le=5)
    movie_id: int
    title: str
    predicted_rating: float


class SvdRecommendationsResponse(BaseModel):
    user_id: int
    recommendations: list[SvdRecommendationItem]
