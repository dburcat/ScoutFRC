"""
video_downloader.py
-------------------
Downloads match videos from YouTube (via TBA video_url) to a temporary file
for CV processing. The caller is responsible for deleting the file after use —
videos are never stored permanently.

Usage:
    with download_video_temp(video_url) as path:
        process(path)
    # file is automatically deleted on context exit
"""
from __future__ import annotations

import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoDownloadError(Exception):
    """Raised when a video cannot be downloaded."""


@contextmanager
def download_video_temp(video_url: str, match_id: int):
    """
    Context manager — downloads video_url to a temp file, yields the Path,
    then deletes the file on exit regardless of success or failure.

    with download_video_temp(url, match_id=123) as path:
        run_cv_pipeline(path)
    # temp file is gone here — no disk accumulation
    """
    tmp_path: Path | None = None
    try:
        tmp_path = _download(video_url, match_id)
        yield tmp_path
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
                logger.debug("Deleted temp video: %s", tmp_path)
            except Exception as exc:
                logger.warning("Failed to delete temp video %s: %s", tmp_path, exc)


def _download(video_url: str, match_id: int) -> Path:
    """Download video to a named temp file. Returns the Path."""
    try:
        import yt_dlp  # type: ignore[import-untyped]
        from yt_dlp.utils import match_filter_func, DownloadError  # type: ignore[import-untyped]
    except ImportError:
        raise VideoDownloadError(
            "yt-dlp is not installed. Add 'yt-dlp>=2024.1.0' to requirements.txt "
            "and run pip install -r requirements.txt."
        )

    # Use a named temp file so we know the path before yt-dlp writes it.
    # delete=False so yt-dlp can write to it; we delete it ourselves later.
    fd, tmp_str = tempfile.mkstemp(suffix=".mp4", prefix=f"match_{match_id}_")
    os.close(fd)  # yt-dlp opens its own handle
    tmp_path = Path(tmp_str)

    # Build options as Any to avoid type-checker complaints about yt-dlp's
    # untyped params dict — the values are all correct at runtime.
    from typing import Any
    ydl_opts: dict[str, Any] = {
        # Write to our specific temp path (without extension — yt-dlp adds it)
        "outtmpl": str(tmp_path.with_suffix("")),
        # Prefer mp4, fall back to best available
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        # Merge into mp4 container
        "merge_output_format": "mp4",
        # Don't print progress to stdout
        "quiet": True,
        "no_warnings": True,
        # Limit download speed to avoid hammering YouTube (10 MB/s)
        "ratelimit": 10 * 1024 * 1024,
        # Abort if video is longer than 20 minutes (match videos are ~3 min)
        "match_filter": match_filter_func("duration < 1200"),
    }

    logger.info("Downloading video for match %d: %s", match_id, video_url)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            ydl.download([video_url])
    except DownloadError as exc:
        # Clean up the empty temp file on failure
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise VideoDownloadError(f"yt-dlp failed for {video_url}: {exc}") from exc

    # yt-dlp may have written to the path without the suffix we gave
    # (it strips and re-adds extensions). Check both possibilities.
    if not tmp_path.exists():
        # yt-dlp wrote match_123_.mp4 instead of match_123_.mp4 (no double suffix)
        alt = tmp_path.with_suffix("").with_suffix(".mp4")
        if alt.exists():
            tmp_path = alt
        else:
            raise VideoDownloadError(
                f"yt-dlp finished but output file not found at {tmp_path}"
            )

    size_mb = tmp_path.stat().st_size / (1024 * 1024)
    logger.info(
        "Downloaded video for match %d: %.1f MB → %s", match_id, size_mb, tmp_path
    )
    return tmp_path