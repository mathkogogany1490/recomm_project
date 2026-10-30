
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.redis_client import redis_client

# 회원 테이블 등록
from app.auth import model as auth_model

# 현재 연결하는 유일한 라우터
from app.auth.web import router as auth_router
from app.svd.web import router as svd_router
from app.mf.web import router as mf_router
from app.transformer.web import router as transformer_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    redis_client.ping()

    yield

    redis_client.close()
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(svd_router)
app.include_router(mf_router)
app.include_router(transformer_router)