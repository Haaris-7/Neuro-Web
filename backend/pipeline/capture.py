import asyncio
import json
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from pipeline.url_validator import validate_url


def _redirect_hop_count(response) -> int:
    if response is None:
        return 0
    n = 0
    r = response.request
    while r.redirected_from:
        n += 1
        r = r.redirected_from
    return n


async def capture_website(job_id: str, url: str, config: dict[str, Any]) -> dict[str, str]:
    data_root = Path(config["data_dir"]).resolve()
    captures_root = (data_root / "captures").resolve()
    job_dir = (captures_root / job_id).resolve()
    job_dir.relative_to(data_root)
    job_dir.mkdir(parents=True, exist_ok=True)
    video_sub = (job_dir / "video_raw").resolve()
    video_sub.relative_to(data_root)
    video_sub.mkdir(parents=True, exist_ok=True)
    vw = int(config["viewport_w"])
    vh = int(config["viewport_h"])
    duration = float(config["capture_duration"])
    nav_timeout = int(config["navigation_timeout_ms"])
    default_timeout = int(config["default_timeout_ms"])
    max_redirects = int(config["max_redirects"])
    max_video_mb = int(config["max_video_size_mb"])
    screenshot_path = (job_dir / "page.png").resolve()
    screenshot_path.relative_to(data_root)
    text_path = (job_dir / "visible_text.txt").resolve()
    text_path.relative_to(data_root)
    bbox_path = (job_dir / "bounding_boxes.json").resolve()
    bbox_path.relative_to(data_root)
    timeline_path = (job_dir / "scroll_timeline.json").resolve()
    timeline_path.relative_to(data_root)
    final_url = url
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                viewport={"width": vw, "height": vh},
                record_video_dir=str(video_sub),
                record_video_size={"width": vw, "height": vh},
                permissions=[],
                ignore_https_errors=False,
            )
            context.set_default_timeout(default_timeout)
            context.set_default_navigation_timeout(nav_timeout)
            try:
                page = await context.new_page()
                response = await page.goto(
                    url,
                    wait_until="load",
                    timeout=nav_timeout,
                )
                if _redirect_hop_count(response) > max_redirects:
                    raise ValueError("Exceeded maximum redirects")
                final_url = page.url
                await asyncio.to_thread(validate_url, final_url)
                scroll_height = await page.evaluate(
                    "() => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)"
                )
                max_scroll = max(0.0, float(scroll_height) - float(vh))
                steps = max(1, int(duration * 10))
                step_delay = duration / float(steps)
                scroll_timeline: list[dict[str, Any]] = []
                bbox_samples: list[dict[str, Any]] = []
                t0 = time.perf_counter()
                for i in range(steps + 1):
                    y = (max_scroll * float(i)) / float(steps)
                    await page.evaluate("(yy) => window.scrollTo(0, yy)", y)
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    scroll_timeline.append({"scroll_y": y, "time_ms": elapsed_ms})
                    boxes = await page.evaluate(
                        """() => {
                        const tags = ["section","article","nav","header","footer","button","a","form"];
                        const out = [];
                        const seen = new Set();
                        for (const tag of tags) {
                            for (const el of document.querySelectorAll(tag)) {
                                const r = el.getBoundingClientRect();
                                if (r.width <= 0 || r.height <= 0) continue;
                                const key = tag + ":" + r.x + ":" + r.y + ":" + r.width + ":" + r.height;
                                if (seen.has(key)) continue;
                                seen.add(key);
                                out.push({
                                    tag: tag,
                                    x: r.x,
                                    y: r.y,
                                    width: r.width,
                                    height: r.height,
                                    scroll_y: window.scrollY
                                });
                            }
                        }
                        return out;
                    }"""
                    )
                    bbox_samples.append(
                        {
                            "scroll_y": y,
                            "time_ms": elapsed_ms,
                            "boxes": boxes,
                        }
                    )
                    if i < steps:
                        await asyncio.sleep(step_delay)
                await page.screenshot(path=str(screenshot_path), full_page=True, type="png")
                visible_text = await page.evaluate(
                    "() => (document.body && document.body.innerText) ? document.body.innerText : ''"
                )
                await asyncio.to_thread(
                    text_path.write_text,
                    str(visible_text),
                    encoding="utf-8",
                )
                await asyncio.to_thread(
                    bbox_path.write_text,
                    json.dumps({"samples": bbox_samples}, indent=2),
                    encoding="utf-8",
                )
                await asyncio.to_thread(
                    timeline_path.write_text,
                    json.dumps(scroll_timeline, indent=2),
                    encoding="utf-8",
                )
            finally:
                await context.close()
        finally:
            await browser.close()
    webm_files = sorted(video_sub.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No video file was produced")
    video_file = webm_files[0].resolve()
    video_file.relative_to(data_root)
    max_bytes = max_video_mb * 1024 * 1024
    if video_file.stat().st_size > max_bytes:
        video_file.unlink(missing_ok=True)
        raise ValueError("Recorded video exceeds maximum allowed size")
    final_video = (job_dir / "capture.webm").resolve()
    final_video.relative_to(data_root)
    if final_video.exists():
        final_video.unlink()
    video_file.rename(final_video)
    try:
        video_sub.rmdir()
    except OSError:
        pass
    return {
        "video": str(final_video),
        "screenshot": str(screenshot_path),
        "text": str(text_path),
        "bounding_boxes": str(bbox_path),
        "scroll_timeline": str(timeline_path),
        "final_url": final_url,
    }
