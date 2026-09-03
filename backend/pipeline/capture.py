import asyncio
import json
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from pipeline.media import transcode_to_mp4
from pipeline.url_validator import validate_url

SCROLL_STEPS_PER_SECOND = 10
MAX_SCREENSHOT_HEIGHT_PX = 12000
SCREENSHOT_TIMEOUT_MS = 90000

_DOM_SNAPSHOT_JS = """
() => {
  const sy = window.scrollY;
  const sx = window.scrollX;
  const visible = (el, r) => {
    if (r.width <= 0 || r.height <= 0) return false;
    const cs = window.getComputedStyle(el);
    return cs.visibility !== "hidden" && cs.display !== "none" && parseFloat(cs.opacity || "1") > 0.05;
  };
  const rectOf = (el) => {
    const r = el.getBoundingClientRect();
    return { r, box: { x: r.x + sx, y: r.y + sy, width: r.width, height: r.height } };
  };

  const buttonClass = /\\b(btn|button|cta|submit|primary|secondary)\\b/i;
  const isButtonLike = (el, tag) => {
    if (tag === "button") return true;
    if (tag === "input") return ["submit", "button", "reset"].includes(el.type);
    if (el.getAttribute("role") === "button") return true;
    if (buttonClass.test(el.className || "")) return true;
    const cs = window.getComputedStyle(el);
    return tag === "a" && cs.display !== "inline" && (parseFloat(cs.paddingLeft) >= 8 || parseFloat(cs.borderRadius) > 0);
  };
  const controlText = (el) =>
    (el.innerText || el.value || el.getAttribute("aria-label") || el.getAttribute("title") || "")
      .replace(/\\s+/g, " ").trim().slice(0, 200);

  const regionTags = ["header", "nav", "main", "section", "article", "aside", "footer", "form", "button", "a", "input"];
  const regions = [];
  const seen = new Set();
  for (const tag of regionTags) {
    for (const el of document.querySelectorAll(tag)) {
      if (tag === "input" && !["submit", "button", "reset"].includes(el.type)) continue;
      const { r, box } = rectOf(el);
      if (!visible(el, r)) continue;
      const key = `${tag}:${Math.round(box.x)}:${Math.round(box.y)}:${Math.round(box.width)}:${Math.round(box.height)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const isControl = tag === "button" || tag === "a" || tag === "input";
      regions.push({
        tag,
        ...box,
        text: isControl ? controlText(el) : "",
        is_control: isControl,
        is_button: isControl && isButtonLike(el, tag),
      });
    }
  }

  const textTags = "h1,h2,h3,h4,h5,h6,p,li,td,th,dt,dd,blockquote,figcaption,label,button,a,summary,span,strong,em,small,legend,caption,option";
  const blocks = [];
  for (const el of document.querySelectorAll(textTags)) {
    let own = "";
    for (const node of el.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) own += node.textContent + " ";
    }
    own = own.replace(/\\s+/g, " ").trim();
    if (own.length < 2) continue;
    const { r, box } = rectOf(el);
    if (!visible(el, r)) continue;
    blocks.push({ tag: el.tagName.toLowerCase(), ...box, text: own.slice(0, 1000) });
  }
  blocks.sort((a, b) => (a.y - b.y) || (a.x - b.x));

  const checkedBoxes = [];
  for (const el of document.querySelectorAll('input[type="checkbox"]:checked')) {
    const { r, box } = rectOf(el);
    let label = "";
    if (el.id) {
      const forLabel = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (forLabel) label = forLabel.innerText;
    }
    if (!label) {
      const wrapping = el.closest("label");
      if (wrapping) label = wrapping.innerText;
    }
    if (!label && el.parentElement) label = el.parentElement.innerText;
    if (!label) label = el.getAttribute("aria-label") || el.name || "";
    checkedBoxes.push({ ...box, label: label.replace(/\\s+/g, " ").trim().slice(0, 300) });
  }

  return {
    page_height: Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0),
    regions,
    text_blocks: blocks,
    checked_boxes: checkedBoxes,
  };
}
"""


def _redirect_hop_count(response) -> int:
    if response is None:
        return 0
    n = 0
    request = response.request
    while request.redirected_from:
        n += 1
        request = request.redirected_from
    return n


def _job_paths(job_dir: Path, data_root: Path) -> dict[str, Path]:
    paths = {
        "screenshot": job_dir / "page.png",
        "text": job_dir / "visible_text.txt",
        "dom": job_dir / "dom.json",
        "scroll_timeline": job_dir / "scroll_timeline.json",
        "capture_meta": job_dir / "capture.json",
        "video_webm": job_dir / "capture.webm",
        "video_mp4": job_dir / "capture.mp4",
    }
    for p in paths.values():
        p.resolve().relative_to(data_root)
    return paths


async def _write_json(path: Path, payload: Any) -> None:
    await asyncio.to_thread(
        path.write_text, json.dumps(payload, indent=2), encoding="utf-8"
    )


async def capture_website(job_id: str, url: str, config: dict[str, Any]) -> dict[str, Any]:
    data_root = Path(config["data_dir"]).resolve()
    job_dir = (data_root / "captures" / job_id).resolve()
    job_dir.relative_to(data_root)
    job_dir.mkdir(parents=True, exist_ok=True)
    video_dir = job_dir / "video_raw"
    video_dir.mkdir(parents=True, exist_ok=True)

    viewport_w = int(config["viewport_w"])
    viewport_h = int(config["viewport_h"])
    duration_s = float(config["capture_duration"])
    nav_timeout_ms = int(config["navigation_timeout_ms"])
    default_timeout_ms = int(config["default_timeout_ms"])
    max_redirects = int(config["max_redirects"])
    max_video_bytes = int(config["max_video_size_mb"]) * 1024 * 1024
    paths = _job_paths(job_dir, data_root)

    final_url = url
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                viewport={"width": viewport_w, "height": viewport_h},
                record_video_dir=str(video_dir),
                record_video_size={"width": viewport_w, "height": viewport_h},
                permissions=[],
            )
            context.set_default_timeout(default_timeout_ms)
            context.set_default_navigation_timeout(nav_timeout_ms)
            try:
                recording_started = time.perf_counter()
                page = await context.new_page()
                response = await page.goto(url, wait_until="load", timeout=nav_timeout_ms)
                if _redirect_hop_count(response) > max_redirects:
                    raise ValueError("Exceeded maximum redirects")
                final_url = page.url
                await asyncio.to_thread(validate_url, final_url)

                scroll_height = float(
                    await page.evaluate(
                        "() => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)"
                    )
                )
                max_scroll = max(0.0, scroll_height - viewport_h)
                steps = max(1, int(duration_s * SCROLL_STEPS_PER_SECOND))
                step_delay = duration_s / steps
                timeline: list[dict[str, float]] = []
                t0 = time.perf_counter()
                scroll_offset_s = t0 - recording_started
                for i in range(steps + 1):
                    y = max_scroll * i / steps
                    await page.evaluate("(y) => window.scrollTo(0, y)", y)
                    timeline.append(
                        {
                            "time_ms": int((time.perf_counter() - t0) * 1000),
                            "scroll_y": round(y, 2),
                        }
                    )
                    if i < steps:
                        await asyncio.sleep(step_delay)
                capture_elapsed_s = time.perf_counter() - t0

                dom = await page.evaluate(_DOM_SNAPSHOT_JS)
                visible_text = await page.evaluate(
                    "() => (document.body && document.body.innerText) ? document.body.innerText : ''"
                )
                await page.evaluate("() => window.scrollTo(0, 0)")
                page_height = float(dom.get("page_height") or scroll_height)
                await page.screenshot(
                    path=str(paths["screenshot"]),
                    full_page=True,
                    type="png",
                    animations="disabled",
                    caret="hide",
                    timeout=SCREENSHOT_TIMEOUT_MS,
                    clip={
                        "x": 0,
                        "y": 0,
                        "width": viewport_w,
                        "height": max(viewport_h, min(page_height, MAX_SCREENSHOT_HEIGHT_PX)),
                    },
                )
            finally:
                await context.close()
        finally:
            await browser.close()

    dom["viewport"] = {"width": viewport_w, "height": viewport_h}
    await asyncio.to_thread(paths["text"].write_text, str(visible_text), encoding="utf-8")
    await _write_json(paths["dom"], dom)
    await _write_json(paths["scroll_timeline"], timeline)

    webm_files = sorted(video_dir.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No video file was produced")
    raw_video = webm_files[0]
    if raw_video.stat().st_size > max_video_bytes:
        raw_video.unlink(missing_ok=True)
        raise ValueError("Recorded video exceeds maximum allowed size")
    paths["video_webm"].unlink(missing_ok=True)
    raw_video.rename(paths["video_webm"])
    try:
        video_dir.rmdir()
    except OSError:
        pass

    mp4 = await asyncio.to_thread(
        transcode_to_mp4,
        paths["video_webm"],
        paths["video_mp4"],
        start_s=scroll_offset_s,
        duration_s=capture_elapsed_s,
    )
    video_path = mp4 if mp4 is not None else paths["video_webm"]

    meta = {
        "video": str(video_path),
        "video_webm": str(paths["video_webm"]),
        "video_trimmed": mp4 is not None,
        "video_offset_s": 0.0 if mp4 is not None else round(scroll_offset_s, 3),
        "screenshot": str(paths["screenshot"]),
        "text": str(paths["text"]),
        "dom": str(paths["dom"]),
        "scroll_timeline": str(paths["scroll_timeline"]),
        "final_url": final_url,
        "viewport_w": viewport_w,
        "viewport_h": viewport_h,
        "page_height": dom.get("page_height"),
        "screenshot_height": int(max(viewport_h, min(page_height, MAX_SCREENSHOT_HEIGHT_PX))),
        "duration_s": round(capture_elapsed_s, 2),
        "n_regions": len(dom.get("regions", [])),
        "n_text_blocks": len(dom.get("text_blocks", [])),
    }
    await _write_json(paths["capture_meta"], meta)
    return meta
