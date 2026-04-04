import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.jobs import router as jobs_router
from api.stream import router as stream_router
from config import settings
from database import init_db, reconcile_stale_jobs
from pipeline.model_manager import GPUInfo, ModelManager
from worker import worker_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _log_gpu_info() -> None:
    gpu = GPUInfo.detect()
    if not gpu.available:
        logger.warning(
            "No CUDA GPU detected — TRIBE v2 inference will not be available. "
            "Install an NVIDIA GPU with 16GB+ VRAM for brain analysis."
        )
        return
    for dev in gpu.devices:
        status = "OK" if dev["sufficient"] else "INSUFFICIENT"
        logger.info(
            "GPU %d: %s — %.1f GB VRAM [%s]",
            dev["index"],
            dev["name"],
            dev["total_vram_gb"],
            status,
        )


async def _warm_up_model() -> None:
    """Load TRIBE v2 model eagerly on startup (off the event loop)."""
    mgr = ModelManager.get()
    await asyncio.to_thread(mgr.load_model)
    if mgr.is_loaded:
        await asyncio.to_thread(mgr.warm_up)
    else:
        logger.warning(
            "TRIBE v2 model not loaded — inference disabled. Reason: %s",
            mgr.error or "unknown",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await reconcile_stale_jobs()

    _log_gpu_info()
    await _warm_up_model()

    stop = asyncio.Event()
    task = asyncio.create_task(worker_loop(stop))
    app.state.worker_stop = stop
    app.state.worker_task = task
    app.state.model_manager = ModelManager.get()
    yield
    stop.set()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
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


@app.get("/health")
async def health():
    mgr = ModelManager.get()
    return mgr.health()


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
