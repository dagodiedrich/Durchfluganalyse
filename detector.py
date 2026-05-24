from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple

import cv2
import numpy as np


@dataclass
class Event:
    event_id: int
    start_sec: float
    end_sec: float
    max_area: float
    bbox: Tuple[int, int, int, int]
    clip_name: str
    event_type: str


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    cleaned = "".join("_" if ch in '<>:"/\\|?*' else ch for ch in name).strip()
    return cleaned or "video"


def clips_folder_for_video(video_path: str) -> str:
    stem = _safe_name(Path(video_path).stem)
    return f"Analyseclips_{stem}"


def _prepare_motion_mask(frame: np.ndarray, subtractor: cv2.BackgroundSubtractor) -> np.ndarray:
    fg = subtractor.apply(frame)
    fg = cv2.GaussianBlur(fg, (5, 5), 0)

    kernel = np.ones((3, 3), dtype=np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel, iterations=2)
    fg = cv2.morphologyEx(fg, cv2.MORPH_DILATE, kernel, iterations=1)
    _, fg = cv2.threshold(fg, 170, 255, cv2.THRESH_BINARY)
    return fg


def analyze_video(
    video_path: str,
    output_dir: str,
    min_area: int = 70,
    max_area: int = 22000,
    min_speed_px_s: float = 22.0,
    min_displacement_px: float = 180.0,
    max_event_duration_s: float = 2.2,
    clip_padding_sec: float = 0.6,
    min_event_frames: int = 4,
    gap_tolerance_frames: int = 4,
    progress_callback: Callable[[int, int], None] | None = None,
) -> Dict:
    started = time.perf_counter()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_sec = frame_count / fps if fps > 0 else 0.0

    out_path = Path(output_dir)
    _ensure_output_dir(out_path)
    video_stem = Path(video_path).name
    clips_subdir = clips_folder_for_video(video_path)
    clips_dir = out_path / "clips" / clips_subdir
    _ensure_output_dir(clips_dir)

    subtractor = cv2.createBackgroundSubtractorMOG2(history=700, varThreshold=20, detectShadows=False)

    events: List[Event] = []
    tracks: Dict[int, Dict] = {}
    next_track_id = 1
    frame_idx = -1
    frames_with_candidates = 0
    total_candidates = 0
    tracks_created = 0

    def finalize_track(track: Dict) -> None:
        displacement = math.dist(track["first_center"], track["last_center"])
        duration = max(0.0, track["last_sec"] - track["start_sec"])
        if track["frames"] < min_event_frames:
            return
        appearance_duration_hi = max_event_duration_s * 1.75
        if duration > max_event_duration_s * 1.8:
            return
        is_pass = (
            track["speed_ok_frames"] >= 2
            and displacement >= min_displacement_px
            and duration <= max_event_duration_s
        )
        # Nur echte Bewegung (mehrere schnelle Frames + Mindestweg), laenger als
        # ein Durchflug — statische MOG2-Flecken fallen so weg.
        is_appearance = (
            not is_pass
            and track["speed_ok_frames"] >= 2
            and displacement >= min_displacement_px
            and duration > max_event_duration_s
            and duration <= appearance_duration_hi
            and track["frames"] >= (min_event_frames + 2)
            and track["max_area"] >= (min_area * 1.5)
        )
        if not (is_pass or is_appearance):
            return

        clip_idx = len(events) + 1
        event_type = "durchflug" if is_pass else "tier-erscheinung"
        clip_prefix = "bird_pass" if is_pass else "animal_appearance"
        clip_name = f"{clip_prefix}_{clip_idx:04d}.mp4"
        events.append(
            Event(
                event_id=clip_idx,
                start_sec=track["start_sec"],
                end_sec=track["last_sec"],
                max_area=track["max_area"],
                bbox=track["bbox"],
                clip_name=clip_name,
                event_type=event_type,
            )
        )

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        if progress_callback and frame_idx % 30 == 0:
            progress_callback(frame_idx, frame_count)
        t = frame_idx / fps

        fg = _prepare_motion_mask(frame, subtractor)
        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area or area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            # Prefer compact small objects over diffuse movement regions.
            aspect_ratio = (w / h) if h else 0.0
            box_area = float(w * h) if (w and h) else 0.0
            fill_ratio = float(area) / box_area if box_area > 0.0 else 0.0
            if w < 2 or h < 2:
                continue
            if aspect_ratio > 10.0 or aspect_ratio < 0.08:
                continue
            if fill_ratio < 0.14:
                continue
            candidates.append((area, (x, y, w, h), (x + w / 2.0, y + h / 2.0)))
        if candidates:
            frames_with_candidates += 1
            total_candidates += len(candidates)

        for track in tracks.values():
            track["updated"] = False

        for area, bbox, center in candidates:
            best_id = None
            best_dist = 999999.0
            for track_id, track in tracks.items():
                dt = max(t - track["last_sec"], 1.0 / fps)
                max_match_dist = max(25.0, min_speed_px_s * dt * 1.6)
                dist = math.dist(center, track["last_center"])
                if dist < best_dist and dist <= max_match_dist:
                    best_dist = dist
                    best_id = track_id

            if best_id is None:
                tracks[next_track_id] = {
                    "start_sec": t,
                    "last_sec": t,
                    "first_center": center,
                    "last_center": center,
                    "frames": 1,
                    "missing_frames": 0,
                    "max_area": area,
                    "bbox": bbox,
                    "speed_ok_frames": 0,
                    "updated": True,
                }
                next_track_id += 1
                tracks_created += 1
                continue

            track = tracks[best_id]
            dt = max(t - track["last_sec"], 1.0 / fps)
            speed = math.dist(center, track["last_center"]) / dt
            if speed >= min_speed_px_s:
                track["speed_ok_frames"] += 1
            track["frames"] += 1
            track["missing_frames"] = 0
            track["last_sec"] = t
            track["last_center"] = center
            track["updated"] = True
            if area > track["max_area"]:
                track["max_area"] = area
                track["bbox"] = bbox

        to_delete = []
        for track_id, track in tracks.items():
            if not track["updated"]:
                track["missing_frames"] += 1
            if track["missing_frames"] > gap_tolerance_frames:
                finalize_track(track)
                to_delete.append(track_id)
        for track_id in to_delete:
            del tracks[track_id]

    cap.release()
    if progress_callback:
        progress_callback(max(frame_idx + 1, 0), frame_count)
    if frame_idx < 0:
        raise RuntimeError(
            "Video konnte nicht dekodiert werden (0 Frames gelesen). "
            "Bitte pruefe Codec/Container oder nutze eine MP4-H264 Datei."
        )
    for track in tracks.values():
        finalize_track(track)

    filtered_events = [
        ev for ev in events if (ev.end_sec - ev.start_sec) > (1.0 / fps)
    ]
    if not filtered_events:
        filtered_events = events

    _export_clips(video_path, clips_dir, filtered_events, padding_sec=clip_padding_sec)

    clip_rel_prefix = f"output/clips/{clips_subdir}"
    file_size_bytes = None
    try:
        file_size_bytes = Path(video_path).stat().st_size
    except OSError:
        pass

    return {
        "video_path": video_path,
        "video_filename": video_stem,
        "clips_folder": str(clips_dir),
        "clips_folder_rel": clip_rel_prefix,
        "file_size_bytes": file_size_bytes,
        "fps": fps,
        "frame_count": frame_count,
        "analyzed_frames": frame_idx + 1,
        "width": width,
        "height": height,
        "duration_sec": duration_sec,
        "detections": [
            {
                "id": ev.event_id,
                "start_sec": round(ev.start_sec, 2),
                "end_sec": round(ev.end_sec, 2),
                "duration_sec": round(ev.end_sec - ev.start_sec, 2),
                "max_area": round(ev.max_area, 1),
                "event_type": ev.event_type,
                "bbox": {"x": ev.bbox[0], "y": ev.bbox[1], "w": ev.bbox[2], "h": ev.bbox[3]},
                "clip_path": f"{clip_rel_prefix}/{ev.clip_name}",
            }
            for ev in filtered_events
        ],
        "total_passes": len(filtered_events),
        "processing_sec": round(time.perf_counter() - started, 2),
        "debug": {
            "frames_with_candidates": frames_with_candidates,
            "total_candidates": total_candidates,
            "tracks_created": tracks_created,
            "events_before_filter": len(events),
            "events_after_filter": len(filtered_events),
        },
    }


def _export_clips(video_path: str, clips_dir: Path, events: List[Event], padding_sec: float = 0.6) -> None:
    if not events:
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    total_duration = frame_count / fps if fps > 0 else 0.0

    intervals = []
    for ev in events:
        start = max(0.0, ev.start_sec - padding_sec)
        end = min(total_duration, ev.end_sec + padding_sec)
        intervals.append((start, end, ev.clip_name))

    intervals.sort(key=lambda x: x[0])
    preferred_codecs = ["avc1", "H264", "mp4v"]

    for start, end, clip_name in intervals:
        start_frame = max(0, int(start * fps))
        end_frame = min(max(frame_count - 1, 0), int(end * fps))
        if end_frame <= start_frame:
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        out_file = str(clips_dir / clip_name)
        writer = None
        for codec in preferred_codecs:
            writer_try = cv2.VideoWriter(out_file, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
            if writer_try.isOpened():
                writer = writer_try
                break
            writer_try.release()
        if writer is None:
            continue

        current_frame = start_frame
        while current_frame <= end_frame:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
            current_frame += 1
        writer.release()

    cap.release()
