from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.jobs import router as jobs_router
from api.stream import router as stream_router
from config import settings
from database import init_db, reconcile_stale_jobs
from worker import worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await reconcile_stale_jobs()
    stop = __import__("asyncio").Event()
    task = __import__("asyncio").create_task(worker_loop(stop))
    app.state.worker_stop = stop
    app.state.worker_task = task
    yield
    stop.set()
    task.cancel()
    try:
        await task
    except __import__("asyncio").CancelledError:
        pass


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router)
app.include_router(stream_router)


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
