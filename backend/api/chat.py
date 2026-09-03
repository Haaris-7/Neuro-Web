"""Report-grounded chatbot streamed over SSE from OpenAI- or Anthropic-compatible APIs."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from config import settings
from engine.report import load_report

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_HISTORY = 12
MAX_MESSAGE_CHARS = 4000
MAX_TOKENS = 700
TOP_REGIONS = 10

SYSTEM_PROMPT = """You are the analysis assistant for Neuro Web, a tool that predicts how a website \
engages the brain by running Meta's TRIBE v2 brain-encoding model on a scrolling screen \
recording of the page. Predictions are simulated fMRI responses on the fsaverage5 cortical \
mesh (about 20,000 vertices), summarised into five functional networks (visual, attention, \
emotional, language, default mode) and 0-10 scores where 5 is typical for this page and the \
tails mark networks that stand out. Dark patterns come from rule-based detectors over the \
page text and layout.

Answer questions about THIS report using only the JSON data below. Be concrete: cite scores, \
regions, times and evidence text. Explain neuroscience terms plainly. Make clear that these are \
model predictions, not measurements from real people, and never present them as clinical or \
causal claims. If the report says inference_backend is "mock", say up front that the numbers \
are synthetic placeholders produced without the TRIBE v2 model. If something is not in the \
report, say so instead of guessing.

REPORT JSON:
"""


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatTurn] = Field(default_factory=list)


def _compact_report(report: dict[str, Any]) -> dict[str, Any]:
    scores = report.get("scores", {})
    timeline = report.get("timeline", {})
    dark = report.get("dark_patterns", {})
    return {
        "url": report.get("url"),
        "metadata": report.get("metadata"),
        "scores": {
            "attention_score": scores.get("attention_score"),
            "emotion_score": scores.get("emotion_score"),
            "impact_score": scores.get("impact_score"),
            "temporal_variance": scores.get("temporal_variance"),
        },
        "network_breakdown": scores.get("network_breakdown", []),
        "top_regions": scores.get("region_breakdown", [])[:TOP_REGIONS],
        "quietest_regions": scores.get("region_breakdown", [])[-3:],
        "dark_patterns": {
            "score": dark.get("score"),
            "counts": dark.get("counts"),
            "patterns": [
                {k: p.get(k) for k in ("pattern_type", "confidence", "evidence_text")}
                for p in dark.get("patterns", [])
            ],
        },
        "timeline": {
            "duration_s": timeline.get("duration_s"),
            "peaks": timeline.get("peaks", []),
        },
        "summaries": report.get("template_summaries"),
    }


def _messages(payload: ChatRequest) -> list[dict[str, str]]:
    history = [t.model_dump() for t in payload.history[-MAX_HISTORY:]]
    return history + [{"role": "user", "content": payload.message}]


async def _stream_openai(
    system: str, messages: list[dict[str, str]], client: httpx.AsyncClient
) -> AsyncIterator[str]:
    base = (settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    body = {
        "model": settings.LLM_MODEL,
        "stream": True,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system}] + messages,
    }
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
    async with client.stream("POST", f"{base}/chat/completions", json=body, headers=headers) as resp:
        await _raise_for_status(resp)
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                yield delta


async def _stream_anthropic(
    system: str, messages: list[dict[str, str]], client: httpx.AsyncClient
) -> AsyncIterator[str]:
    base = (settings.LLM_BASE_URL or "https://api.anthropic.com").rstrip("/")
    body = {
        "model": settings.LLM_MODEL,
        "stream": True,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": messages,
    }
    headers = {"x-api-key": settings.LLM_API_KEY or "", "anthropic-version": "2023-06-01"}
    async with client.stream("POST", f"{base}/v1/messages", json=body, headers=headers) as resp:
        await _raise_for_status(resp)
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if event.get("type") == "content_block_delta":
                text = event.get("delta", {}).get("text")
                if text:
                    yield text
            elif event.get("type") == "message_stop":
                break


async def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    detail = (await resp.aread()).decode("utf-8", errors="replace")[:500]
    raise HTTPException(status_code=502, detail=f"LLM provider error {resp.status_code}: {detail}")


@router.post("/{job_id}")
async def chat(job_id: str, payload: ChatRequest) -> EventSourceResponse:
    if not settings.llm_available:
        raise HTTPException(status_code=503, detail="LLM chat is not configured (set LLM_API_KEY)")
    report = await asyncio.to_thread(load_report, job_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    system = SYSTEM_PROMPT + json.dumps(_compact_report(report), separators=(",", ":"))
    messages = _messages(payload)
    stream = _stream_anthropic if settings.LLM_PROVIDER == "anthropic" else _stream_openai

    async def publisher():
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0)) as client:
            try:
                async for chunk in stream(system, messages, client):
                    yield {"data": json.dumps({"content": chunk})}
            except HTTPException as exc:
                yield {"data": json.dumps({"error": exc.detail})}
            except httpx.HTTPError as exc:
                yield {"data": json.dumps({"error": f"LLM request failed: {exc}"})}
        yield {"data": "[DONE]"}

    return EventSourceResponse(publisher())
