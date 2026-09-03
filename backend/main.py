import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.assets import router as assets_router
from api.chat import router as chat_router
from api.files import router as files_router
from api.jobs import router as jobs_router
from api.stream import router as stream_router
from config import settings
from database import init_db, reconcile_stale_jobs
from engine.atlas import load_atlas
from engine.mesh_export import ensure_brain_mesh
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
        logger.warning("No CUDA GPU detected; TRIBE v2 inference is unavailable on this machine")
        return
    for dev in gpu.devices:
        logger.info(
            "GPU %d: %s (%.1f GB VRAM) %s",
            dev["index"],
            dev["name"],
            dev["total_vram_gb"],
            "OK" if dev["sufficient"] else "below the 16 GB recommended for video+text",
        )


async def _prepare_assets() -> None:
    try:
        await asyncio.to_thread(load_atlas)
        await asyncio.to_thread(ensure_brain_mesh)
    except Exception:
        logger.warning("Could not prepare atlas/mesh assets at startup", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await reconcile_stale_jobs()
    _log_gpu_info()
    logger.info(
        "Inference backend: %s (modalities: %s); LLM chat: %s",
        settings.INFERENCE_BACKEND,
        ",".join(settings.TRIBE_MODALITIES),
        settings.LLM_PROVIDER if settings.llm_available else "disabled",
    )
    await _prepare_assets()

    manager = ModelManager.get()
    model_ready = asyncio.create_task(_load_model(manager))
    stop = asyncio.Event()
    worker = asyncio.create_task(worker_loop(stop, model_ready))
    app.state.model_manager = manager
    try:
        yield
    finally:
        stop.set()
        for task in (worker, model_ready):
            task.cancel()
        await asyncio.gather(worker, model_ready, return_exceptions=True)


async def _load_model(manager: ModelManager) -> None:
    await asyncio.to_thread(manager.load_model)
    if not manager.inference_ready:
        logger.warning("Inference disabled: %s", manager.error or "unknown reason")


app = FastAPI(title="Neuro Web API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router)
app.include_router(stream_router)
app.include_router(files_router)
app.include_router(assets_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict:
    return ModelManager.get().health()


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=settings.BACKEND_PORT, reload=False)


if __name__ == "__main__":
    main()
