from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.routers import auth, jobs, knowledge_base, labels, papers, prompts, settings, workspace
from app.seed import seed_defaults


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    yield


app = FastAPI(title="AutoPaperReader", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(labels.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(knowledge_base.router, prefix="/api")
app.include_router(workspace.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
