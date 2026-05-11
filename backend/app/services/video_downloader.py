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
    tmp_dir: Path | None = None
    try:
        tmp_path, tmp_dir = _download(video_url, match_id)
        yield tmp_path
    finally:
        if tmp_dir and tmp_dir.exists():
            try:
                import shutil as _shutil
                _shutil.rmtree(tmp_dir)
                logger.debug("Deleted temp video dir: %s", tmp_dir)
            except Exception as exc:
                logger.warning("Failed to delete temp video dir %s: %s", tmp_dir, exc)


def _ffmpeg_available() -> bool:
    """Check if ffmpeg is installed and accessible on PATH."""
    import shutil
    return shutil.which("ffmpeg") is not None


def _download(video_url: str, match_id: int) -> tuple[Path, Path]:
    """Download video to a temp directory. Returns (file_path, dir_path)."""
    try:
        import yt_dlp  # type: ignore[import-untyped]
        from yt_dlp.utils import match_filter_func, DownloadError  # type: ignore[import-untyped]
    except ImportError:
        raise VideoDownloadError(
            "yt-dlp is not installed. Add 'yt-dlp>=2024.1.0' to requirements.txt "
            "and run pip install -r requirements.txt."
        )

    import tempfile as _tempfile

    # Use a temp *directory* so yt-dlp can choose the filename+extension freely.
    # We then glob for whatever it wrote rather than guessing the extension.
    tmp_dir = Path(_tempfile.mkdtemp(prefix=f"match_{match_id}_"))
    tmp_path: Path | None = None  # resolved after download

    # Build options as Any to avoid type-checker complaints about yt-dlp's
    # untyped params dict — the values are all correct at runtime.
    from typing import Any
    ydl_opts: dict[str, Any] = {
        # Let yt-dlp pick the filename; we discover it via glob afterward.
        "outtmpl": str(tmp_dir / "video.%(ext)s"),
        # Explicitly require H.264 (avc1) video — YouTube also serves AV1 inside
        # .mp4 containers, and OpenCV on ARM64/Linux cannot software-decode AV1.
        # When AV1 is selected, cap.read() returns False on every frame and
        # 0 tracks are produced. The fallback chain ensures we always get H.264.
        "format": (
            "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo[vcodec^=avc1]+bestaudio"
            "/best[vcodec^=avc1][ext=mp4]"
            "/best[ext=mp4]/best"
            if _ffmpeg_available()
            else "best[vcodec^=avc1][ext=mp4]/best[vcodec^=avc1]/best[ext=mp4]/best"
        ),
        **({"merge_output_format": "mp4"} if _ffmpeg_available() else {}),
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
        # Clean up the temp directory on failure
        import shutil as _shutil
        _shutil.rmtree(tmp_dir, ignore_errors=True)
        raise VideoDownloadError(f"yt-dlp failed for {video_url}: {exc}") from exc

    # Discover what yt-dlp actually wrote — it controls the extension
    written = list(tmp_dir.glob("video.*"))
    if not written:
        import shutil as _shutil
        _shutil.rmtree(tmp_dir, ignore_errors=True)
        raise VideoDownloadError(
            f"yt-dlp finished but output file not found in {tmp_dir} — "
            "video may be private, age-restricted, or unavailable."
        )
    tmp_path = written[0]

    size_mb = tmp_path.stat().st_size / (1024 * 1024)
    if size_mb == 0:
        import shutil as _shutil
        _shutil.rmtree(tmp_dir, ignore_errors=True)
        raise VideoDownloadError(
            f"yt-dlp produced a 0-byte file for {video_url} — "
            "video may be private, age-restricted, or unavailable."
        )
    logger.info(
        "Downloaded video for match %d: %.1f MB → %s", match_id, size_mb, tmp_path
    )
    return tmp_path, tmp_dir