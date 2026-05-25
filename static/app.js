const form = document.getElementById("analyze-form");
const statusBox = document.getElementById("statusBox");
const liveText = document.getElementById("liveText");
const progressBar = document.getElementById("progressBar");
const progressPercent = document.getElementById("progressPercent");
const refreshBtn = document.getElementById("refreshBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const videoCheckboxList = document.getElementById("videoCheckboxList");
const selectAllVideosBtn = document.getElementById("selectAllVideos");
const selectNoVideosBtn = document.getElementById("selectNoVideos");
const uploadDirEl = document.getElementById("upload-dir");
const bodyEl = document.getElementById("result-body");
const totalEl = document.getElementById("total-passes");
const durationEl = document.getElementById("duration");
const fpsEl = document.getElementById("fps");
const processingEl = document.getElementById("processing");
const previewEl = document.getElementById("preview");
const debugInfoEl = document.getElementById("debug-info");
const uploadPathViewEl = document.getElementById("upload-path-view");
const clipsDirViewEl = document.getElementById("clips-dir-view");
const videoListEl = document.getElementById("video-list");
const clipListEl = document.getElementById("clip-list");
const viewerHintEl = document.getElementById("viewer-hint");

let pollTimer = null;
let currentJobId = null;
let pollFailures = 0;

function setStatus(text, kind = "") {
  statusBox.className = `status ${kind}`;
  statusBox.textContent = text;
}

function setProgress(value, label) {
  const pct = Math.max(0, Math.min(100, Math.round((value || 0) * 100)));
  progressBar.style.width = `${pct}%`;
  progressPercent.textContent = `${pct}%`;
  liveText.textContent = label || (pct > 0 ? `Analyse: ${pct}%` : "Kein Job aktiv");
}

function getSelectedVideos() {
  return Array.from(videoCheckboxList.querySelectorAll('input[type="checkbox"][name="video"]:checked'))
    .map((el) => el.value);
}

function setAllVideoChecks(checked) {
  videoCheckboxList.querySelectorAll('input[type="checkbox"][name="video"]').forEach((el) => {
    el.checked = checked;
  });
  updateAnalyzeButtonState();
}

function updateAnalyzeButtonState() {
  const selected = getSelectedVideos();
  analyzeBtn.disabled = selected.length === 0;
}

function renderResult(data) {
  totalEl.textContent = data.total_passes ?? 0;
  durationEl.textContent = data.duration_sec != null ? Number(data.duration_sec).toFixed(1) : "-";
  fpsEl.textContent = data.fps ? Number(data.fps).toFixed(1) : "-";
  processingEl.textContent = data.processing_sec != null ? `${Number(data.processing_sec).toFixed(1)}s` : "-";
  const dbg = data.debug || {};
  let debugText = `Debug: Kandidat-Frames ${dbg.frames_with_candidates ?? 0}, Kandidaten ${dbg.total_candidates ?? 0}, Tracks ${dbg.tracks_created ?? 0}, Events ${dbg.events_after_filter ?? 0}`;
  if (data.clips_folder_rel) {
    debugText += ` | Clips: ${data.clips_folder_rel}`;
  }
  if (data.pdf_path) {
    debugText += ` | PDF: /${data.pdf_path}`;
  }
  debugInfoEl.textContent = debugText;

  const rows = data.detections || [];
  if (!rows.length) {
    bodyEl.innerHTML = '<tr><td colspan="6" class="empty">Keine relevanten Events erkannt.</td></tr>';
    previewEl.removeAttribute("src");
    if (viewerHintEl) {
      viewerHintEl.textContent = "Keine Clips vorhanden. Starte eine Analyse fuer die Vorschau.";
    }
    return;
  }

  bodyEl.innerHTML = rows.map((d) => `
    <tr>
      <td>${d.id}</td>
      <td>${d.event_type || "durchflug"}</td>
      <td>${d.start_sec}</td>
      <td>${d.end_sec}</td>
      <td>${d.duration_sec}</td>
      <td><a class="clip-link" data-clip="/${d.clip_path}" href="/${d.clip_path}" target="_blank" rel="noopener">Clip</a></td>
    </tr>
  `).join("");

  bodyEl.querySelectorAll("a[data-clip]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const clipUrl = link.getAttribute("data-clip");
      previewEl.pause();
      previewEl.removeAttribute("src");
      previewEl.src = `${clipUrl}?t=${Date.now()}`;
      previewEl.load();
      previewEl.play().catch(() => {
        if (viewerHintEl) {
          viewerHintEl.textContent = "Clip konnte nicht automatisch gestartet werden. Bitte auf Play klicken oder den Link direkt oeffnen.";
        }
      });
      if (viewerHintEl) {
        viewerHintEl.textContent = `Vorschau geladen: ${clipUrl}`;
      }
    });
  });
}

function renderSimpleList(targetEl, values, emptyText) {
  if (!values || !values.length) {
    targetEl.innerHTML = `<li class="empty">${emptyText}</li>`;
    return;
  }
  targetEl.innerHTML = values
    .map((entry) => `<li title="${entry}">${entry}</li>`)
    .join("");
}

function renderVideoCheckboxes(videos) {
  if (!videos.length) {
    videoCheckboxList.innerHTML = '<p class="empty">Keine Videos im upload-Ordner.</p>';
    analyzeBtn.disabled = true;
    return;
  }
  videoCheckboxList.innerHTML = videos.map((name) => `
    <label class="video-check-item">
      <input type="checkbox" name="video" value="${name.replace(/"/g, "&quot;")}" checked>
      <span title="${name}">${name}</span>
    </label>
  `).join("");
  videoCheckboxList.querySelectorAll('input[type="checkbox"][name="video"]').forEach((el) => {
    el.addEventListener("change", updateAnalyzeButtonState);
  });
  updateAnalyzeButtonState();
}

async function loadClips() {
  const res = await fetch("/api/clips");
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Clip-Liste konnte nicht geladen werden.");
  }
  clipsDirViewEl.textContent = `${data.clips_dir || "output/clips"}/Analyseclips_<Video>/`;
  renderSimpleList(clipListEl, data.clips || [], "Noch keine Clips oder PDFs vorhanden.");
}

async function loadVideos() {
  const res = await fetch("/api/videos");
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Video-Liste konnte nicht geladen werden.");
  }
  const uploadDirPath = data.upload_dir || "upload/";
  uploadDirEl.textContent = uploadDirPath;
  uploadPathViewEl.textContent = uploadDirPath;
  const videos = data.videos || [];
  renderSimpleList(videoListEl, videos, "Keine Videos im upload-Ordner.");
  renderVideoCheckboxes(videos);
}

async function pollJob() {
  if (!currentJobId) return;
  let res;
  let job;
  try {
    res = await fetch(`/api/jobs/${currentJobId}`);
    job = await res.json();
    pollFailures = 0;
  } catch (err) {
    pollFailures += 1;
    if (pollFailures <= 8) {
      setStatus(`Verbindung kurz unterbrochen (${pollFailures}/8) - versuche erneut ...`, "running");
      return;
    }
    clearInterval(pollTimer);
    pollTimer = null;
    analyzeBtn.disabled = getSelectedVideos().length === 0;
    setStatus(`Fehler: Verbindung zur lokalen App verloren (${err.message}).`, "error");
    return;
  }

  if (!res.ok) {
    setStatus(`Fehler: ${job.error || "Job nicht gefunden."}`, "error");
    clearInterval(pollTimer);
    pollTimer = null;
    updateAnalyzeButtonState();
    return;
  }

  setProgress(job.progress || 0, job.message || "Analyse laeuft ...");
  if (job.status === "queued" || job.status === "running") {
    const batchHint = job.total_videos > 1
      ? ` (${job.current_video_index || 0}/${job.total_videos})`
      : "";
    setStatus(`Analyse laeuft${batchHint} ...`, "running");
    return;
  }
  clearInterval(pollTimer);
  pollTimer = null;
  updateAnalyzeButtonState();

  if (job.status === "error") {
    setStatus(`Fehler: ${job.error || "Analyse fehlgeschlagen."}`, "error");
    return;
  }
  if (job.status === "done" && job.result) {
    renderResult(job.result);
    const batch = job.batch_results || [];
    if (batch.length > 1) {
      const summary = batch.map((b) => `${b.filename}: ${b.total_passes} Events`).join(" | ");
      setStatus(`Fertig (${batch.length} Videos): ${summary}`, "done");
    } else {
      const pdfHint = job.result.pdf_path ? ` PDF: /${job.result.pdf_path}` : "";
      setStatus(`Fertig: ${job.result.total_passes} Events erkannt.${pdfHint}`, "done");
    }
    setProgress(1, "Analyse abgeschlossen");
    await loadClips();
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const filenames = getSelectedVideos();
  if (!filenames.length) {
    setStatus("Bitte mindestens ein Video auswaehlen.", "error");
    return;
  }

  const payload = {
    filenames,
    minArea: Number(form.minArea.value),
    maxArea: Number(form.maxArea.value),
    minSpeed: Number(form.minSpeed.value),
    minDisplacement: Number(form.minDisplacement.value),
    maxDuration: Number(form.maxDuration.value),
    clipPadding: Number(form.clipPadding.value),
  };

  analyzeBtn.disabled = true;
  const countLabel = filenames.length === 1 ? filenames[0] : `${filenames.length} Videos`;
  setStatus(`Analyse wird gestartet (${countLabel}) ...`, "running");
  setProgress(0, "Job wird vorbereitet ...");
  bodyEl.innerHTML = '<tr><td colspan="6" class="empty">Analyse laeuft ...</td></tr>';

  try {
    const res = await fetch("/api/analyze-select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Analyse konnte nicht gestartet werden.");
    }

    currentJobId = data.job_id;
    pollFailures = 0;
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => pollJob().catch((err) => setStatus(`Fehler: ${err.message}`, "error")), 1200);
    await pollJob();
  } catch (err) {
    updateAnalyzeButtonState();
    setStatus(`Fehler: ${err.message}`, "error");
  }
});

selectAllVideosBtn.addEventListener("click", () => setAllVideoChecks(true));
selectNoVideosBtn.addEventListener("click", () => setAllVideoChecks(false));

refreshBtn.addEventListener("click", () => {
  Promise.all([loadVideos(), loadClips()])
    .then(() => setStatus("Video- und Clip-Liste aktualisiert.", ""))
    .catch((err) => setStatus(`Fehler: ${err.message}`, "error"));
});

Promise.all([loadVideos(), loadClips()])
  .then(() => setStatus("Bereit fuer Analyse.", ""))
  .catch((err) => setStatus(`Fehler: ${err.message}`, "error"));

previewEl.addEventListener("error", () => {
  if (viewerHintEl) {
    viewerHintEl.textContent = "Browser konnte den Clip nicht dekodieren. Teste den Link in neuem Tab oder pruefe den installierten Video-Codec.";
  }
});
