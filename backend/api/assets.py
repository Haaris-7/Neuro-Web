import asyncio

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from engine.atlas import load_atlas
from engine.mesh_export import ensure_brain_mesh

router = APIRouter(tags=["assets"])

_CACHE_HEADERS = {"Cache-Control": "public, max-age=86400"}


@router.get("/atlas")
async def get_atlas() -> JSONResponse:
    try:
        atlas = await asyncio.to_thread(load_atlas)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Atlas unavailable: {exc}") from exc
    return JSONResponse(atlas.to_payload(), headers=_CACHE_HEADERS)


@router.get("/mesh")
async def get_mesh() -> FileResponse:
    try:
        path = await asyncio.to_thread(ensure_brain_mesh)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Brain mesh unavailable: {exc}") from exc
    return FileResponse(str(path), media_type="model/gltf-binary", headers=_CACHE_HEADERS)
