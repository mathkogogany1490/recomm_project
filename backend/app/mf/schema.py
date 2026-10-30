
from pydantic import BaseModel, Field


class MfKpiResponse(BaseModel):
    mae: float
    mse: float
    rmse: float

    rating_count: int
    user_count: int
    movie_count: int
    factors: int

    evaluation: str


class MfRecommendationItem(BaseModel):
    rank: int = Field(ge=1, le=5)
    movie_id: int
    title: str
    genres: str
    predicted_rating: float


class MfRecommendationsResponse(BaseModel):
    user_id: int
    recommendations: list[MfRecommendationItem]
