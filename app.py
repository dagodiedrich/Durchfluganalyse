from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory

from detector import analyze_video, clips_folder_for_video
from report_pdf import generate_analysis_pdf


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    RESOURCE_DIR = Path(sys._MEIPASS)
    RUNTIME_DIR = Path(sys.executable).resolve().parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    RUNTIME_DIR = RESOURCE_DIR
UPLOAD_DIR = RUNTIME_DIR / "upload"
OUTPUT_DIR = RUNTIME_DIR / "output"
RESULTS_FILE = OUTPUT_DIR / "last_result.json"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    static_folder=str(RESOURCE_DIR / "static"),
    template_folder=str(RESOURCE_DIR / "templates"),
)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024 * 1024  # 25GB
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _parse_params(form_like):
    min_area = int(form_like.get("minArea", "70"))
    max_area = int(form_like.get("maxArea", "22000"))
    min_speed = float(form_like.get("minSpeed", "22"))
    min_displacement = float(form_like.get("minDisplacement", "180"))
    max_duration = float(form_like.get("maxDuration", "2.2"))
    clip_padding = float(form_like.get("clipPadding", "0.6"))
    return min_area, max_area, min_speed, min_displacement, max_duration, clip_padding


def _params_dict(min_area, max_area, min_speed, min_displacement, max_duration, clip_padding):
    return {
        "min_area": min_area,
        "max_area": max_area,
        "min_speed_px_s": min_speed,
        "min_displacement_px": min_displacement,
        "max_event_duration_s": max_duration,
        "clip_padding_sec": clip_padding,
    }


def _run_analysis(video_path: Path, form_like, progress_callback=None):
    try:
        min_area, max_area, min_speed, min_displacement, max_duration, clip_padding = _parse_params(form_like)
    except ValueError:
        return None, (jsonify({"error": "Ungueltige Parameter."}), 400)

    if min_area < 10 or max_area <= min_area:
        return None, (jsonify({"error": "Flaechen-Parameter sind ungueltig."}), 400)
    if min_speed < 1 or min_displacement < 1 or max_duration <= 0:
        return None, (jsonify({"error": "Bewegungs-Parameter sind ungueltig."}), 400)
    if clip_padding < 0 or clip_padding > 6:
        return None, (jsonify({"error": "Clip-Padding muss zwischen 0 und 6 liegen."}), 400)

    try:
        result = analyze_video(
            str(video_path),
            str(OUTPUT_DIR),
            min_area=min_area,
            max_area=max_area,
            min_speed_px_s=min_speed,
            min_displacement_px=min_displacement,
            max_event_duration_s=max_duration,
            clip_padding_sec=clip_padding,
            progress_callback=progress_callback,
        )
        pdf_name = f"Analysedokumentation_{Path(video_path).stem}.pdf"
        pdf_path = Path(result["clips_folder"]) / pdf_name
        generate_analysis_pdf(
            result,
            pdf_path,
            video_filename=video_path.name,
            analysis_params=_params_dict(
                min_area, max_area, min_speed, min_displacement, max_duration, clip_padding
            ),
        )
        result["pdf_path"] = f"{result['clips_folder_rel']}/{pdf_name}"
        with RESULTS_FILE.open("w", encoding="utf-8") as fp:
            json.dump(result, fp, indent=2, ensure_ascii=True)
        return result, None
    except Exception as exc:
        return None, (jsonify({"error": f"Analyse fehlgeschlagen: {exc}"}), 500)


@app.get("/")
def index():
    return render_template("index.html")


def _list_upload_videos():
    videos = [
        p.name
        for p in sorted(UPLOAD_DIR.iterdir())
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return videos


def _list_exported_clips():
    clips_dir = OUTPUT_DIR / "clips"
    if not clips_dir.exists():
        return []
    entries = []
    for p in sorted(clips_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(OUTPUT_DIR).as_posix()
        if p.suffix.lower() in VIDEO_EXTENSIONS or p.suffix.lower() == ".pdf":
            entries.append(rel)
    return entries


@app.get("/api/videos")
def api_videos():
    return jsonify(
        {
            "upload_dir": str(UPLOAD_DIR),
            "videos": _list_upload_videos(),
        }
    )


@app.get("/api/clips")
def api_clips():
    return jsonify(
        {
            "clips_dir": str((OUTPUT_DIR / "clips")),
            "clips": _list_exported_clips(),
        }
    )


def _update_job(job_id: str, **fields):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(fields)


def _resolve_upload_video(filename: str):
    name = str(filename).strip()
    if not name:
        return None, (jsonify({"error": "Kein Video ausgewaehlt."}), 400)
    video_path = (UPLOAD_DIR / name).resolve()
    try:
        video_path.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return None, (jsonify({"error": "Ungueltiger Dateiname."}), 400)
    if not video_path.exists() or not video_path.is_file():
        return None, (jsonify({"error": f"Datei nicht gefunden: {name}"}), 400)
    if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
        return None, (jsonify({"error": "Nicht unterstuetztes Dateiformat."}), 400)
    return video_path, None


def _run_job(job_id: str, video_paths: list[Path], params: dict):
    started = time.time()
    total_videos = len(video_paths)
    batch_results: list[dict] = []
    last_result = None
    _update_job(
        job_id,
        status="running",
        started_at=started,
        progress=0.0,
        message="Analyse gestartet",
        total_videos=total_videos,
        current_video_index=0,
    )

    for video_index, video_path in enumerate(video_paths):
        current_no = video_index + 1
        _update_job(
            job_id,
            current_video_index=current_no,
            current_filename=video_path.name,
            message=f"Video {current_no}/{total_videos}: {video_path.name}",
        )

        def on_progress(
            frame_idx: int,
            total_frames: int,
            _idx=video_index,
            _current_no=current_no,
        ):
            if total_frames and total_frames > 0:
                if frame_idx >= total_frames:
                    local_p = 0.98
                    frame_msg = "Frame-Analyse fertig, exportiere Clips und PDF..."
                else:
                    local_p = min(0.98, frame_idx / total_frames)
                    frame_msg = f"Analysiere Frame {frame_idx}/{total_frames}"
            else:
                local_p = 0.0
                frame_msg = f"Analysiere Frame {frame_idx}/{total_frames or '?'}"
            overall = min(0.99, (_idx + local_p) / total_videos)
            _update_job(
                job_id,
                progress=overall,
                message=f"Video {_current_no}/{total_videos}: {frame_msg}",
            )

        result, err = _run_analysis(video_path, params, progress_callback=on_progress)
        last_result = result
        if err is not None:
            payload, code = err
            try:
                error_message = payload.get_json().get("error", "Analyse fehlgeschlagen")
            except Exception:
                error_message = "Analyse fehlgeschlagen"
            _update_job(
                job_id,
                status="error",
                progress=1.0,
                finished_at=time.time(),
                elapsed_sec=round(time.time() - started, 2),
                error=f"{video_path.name}: {error_message}",
                http_code=code,
                failed_filename=video_path.name,
                batch_results=batch_results,
            )
            return

        batch_results.append(
            {
                "filename": video_path.name,
                "clips_folder": clips_folder_for_video(str(video_path)),
                "total_passes": result.get("total_passes", 0),
                "pdf_path": result.get("pdf_path"),
            }
        )

    _update_job(
        job_id,
        status="done",
        progress=1.0,
        finished_at=time.time(),
        elapsed_sec=round(time.time() - started, 2),
        message=f"Analyse abgeschlossen ({total_videos} Video(s))",
        result=last_result,
        batch_results=batch_results,
    )


def _requested_filenames(data: dict) -> list[str]:
    raw_list = data.get("filenames")
    if isinstance(raw_list, list):
        names = [str(name).strip() for name in raw_list if str(name).strip()]
        if names:
            return names
    filename = str(data.get("filename", "")).strip()
    return [filename] if filename else []


@app.post("/api/analyze-select")
def api_analyze_select():
    data = request.get_json(silent=True) or {}
    filenames = _requested_filenames(data)
    if not filenames:
        return jsonify({"error": "Kein Video ausgewaehlt."}), 400

    video_paths: list[Path] = []
    for name in filenames:
        video_path, err = _resolve_upload_video(name)
        if err is not None:
            return err
        video_paths.append(video_path)

    job_id = uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0.0,
            "message": "Wartet auf Analyse-Start",
            "filename": filenames[0] if len(filenames) == 1 else None,
            "filenames": filenames,
            "total_videos": len(filenames),
            "current_video_index": 0,
            "created_at": time.time(),
            "result": None,
            "batch_results": [],
            "error": None,
        }

    t = threading.Thread(target=_run_job, args=(job_id, video_paths, data), daemon=True)
    t.start()
    return jsonify({"job_id": job_id, "total_videos": len(filenames)})


@app.get("/api/jobs/<job_id>")
def api_job(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job nicht gefunden."}), 404
    return jsonify(job)


@app.get("/api/result")
def api_result():
    if not RESULTS_FILE.exists():
        return jsonify({"total_passes": 0, "detections": []})
    with RESULTS_FILE.open("r", encoding="utf-8") as fp:
        return jsonify(json.load(fp))


@app.get("/output/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False, threaded=True)
