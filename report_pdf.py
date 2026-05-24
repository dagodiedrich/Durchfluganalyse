from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_sec(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}"


def _event_label(event_type: str) -> str:
    if event_type == "tier-erscheinung":
        return "Tier-Erscheinung"
    return "Durchflug"


def generate_analysis_pdf(
    result: Mapping[str, Any],
    pdf_path: Path,
    video_filename: str,
    analysis_params: Optional[Mapping[str, Any]] = None,
) -> str:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Analysedokumentation",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1a3358"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#4a607f"),
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#244b7a"),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1f2a3a"),
    )

    detections = list(result.get("detections") or [])
    durchfluege = sum(1 for d in detections if d.get("event_type") == "durchflug")
    erscheinungen = sum(1 for d in detections if d.get("event_type") == "tier-erscheinung")
    debug = result.get("debug") or {}
    params = analysis_params or {}

    meta_rows = [
        ["Quelldatei", video_filename],
        ["Vollstaendiger Pfad", str(result.get("video_path", "-"))],
        ["Aufloesung", f"{result.get('width', '-')} x {result.get('height', '-')} px"],
        ["Bildrate (FPS)", _fmt_sec(result.get("fps"))],
        ["Frame-Anzahl", str(result.get("frame_count", "-"))],
        ["Analysierte Frames", str(result.get("analyzed_frames", "-"))],
        ["Videolaenge (s)", _fmt_sec(result.get("duration_sec"))],
        ["Dateigroesse", _format_file_size(result.get("file_size_bytes"))],
    ]

    param_rows = [
        ["Min. Objektflaeche", str(params.get("min_area", "-"))],
        ["Max. Objektflaeche", str(params.get("max_area", "-"))],
        ["Min. Geschwindigkeit (px/s)", str(params.get("min_speed_px_s", "-"))],
        ["Min. Gesamtweg (px)", str(params.get("min_displacement_px", "-"))],
        ["Max. Event-Dauer (s)", str(params.get("max_event_duration_s", "-"))],
        ["Clip Vor-/Nachlauf (s)", str(params.get("clip_padding_sec", "-"))],
    ]

    summary_rows = [
        ["Erkannte Events gesamt", str(result.get("total_passes", 0))],
        ["Davon Durchfluege", str(durchfluege)],
        ["Davon Tier-Erscheinungen", str(erscheinungen)],
        ["Analysezeit (s)", _fmt_sec(result.get("processing_sec"))],
        ["Exportierte Clips", str(len(detections))],
        ["Clips-Ordner", str(result.get("clips_folder", "-"))],
    ]

    story = [
        Paragraph("Analysedokumentation", title_style),
        Paragraph(
            f"Durchfluganalyse &mdash; {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            subtitle_style,
        ),
        Paragraph("Video-Metadaten", section_style),
        _styled_table(meta_rows, col_widths=[5.2 * cm, 11.3 * cm]),
        Spacer(1, 0.2 * cm),
        Paragraph("Verwendete Analyseparameter", section_style),
        _styled_table(param_rows, col_widths=[5.2 * cm, 11.3 * cm]),
        Spacer(1, 0.2 * cm),
        Paragraph("Analyseergebnis (Zusammenfassung)", section_style),
        _styled_table(summary_rows, col_widths=[5.2 * cm, 11.3 * cm]),
        Spacer(1, 0.2 * cm),
        Paragraph("Erkannte Events", section_style),
    ]

    if detections:
        event_rows = [["ID", "Typ", "Start (s)", "Ende (s)", "Dauer (s)", "Max. Flaeche", "Clip"]]
        for det in detections:
            clip_name = Path(str(det.get("clip_path", ""))).name
            event_rows.append(
                [
                    str(det.get("id", "")),
                    _event_label(str(det.get("event_type", "durchflug"))),
                    _fmt_sec(det.get("start_sec")),
                    _fmt_sec(det.get("end_sec")),
                    _fmt_sec(det.get("duration_sec")),
                    str(det.get("max_area", "-")),
                    clip_name,
                ]
            )
        story.append(
            _styled_table(
                event_rows,
                col_widths=[1.0 * cm, 3.0 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm, 2.2 * cm, 4.3 * cm],
                header=True,
            )
        )
    else:
        story.append(Paragraph("Keine relevanten Events erkannt.", body_style))

    if debug:
        story.extend(
            [
                Spacer(1, 0.25 * cm),
                Paragraph("Technische Debug-Informationen", section_style),
                _styled_table(
                    [
                        ["Kandidat-Frames", str(debug.get("frames_with_candidates", 0))],
                        ["Kandidaten gesamt", str(debug.get("total_candidates", 0))],
                        ["Tracks erstellt", str(debug.get("tracks_created", 0))],
                        ["Events vor Filter", str(debug.get("events_before_filter", 0))],
                        ["Events nach Filter", str(debug.get("events_after_filter", 0))],
                    ],
                    col_widths=[5.2 * cm, 11.3 * cm],
                ),
            ]
        )

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Dieses Dokument wurde automatisch durch die Videoanalyse-Software erstellt.",
            ParagraphStyle(
                "Footer",
                parent=body_style,
                fontSize=8,
                textColor=colors.HexColor("#6b7f9c"),
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(story)
    return str(pdf_path)


def _format_file_size(size_bytes: Any) -> str:
    if size_bytes is None:
        return "-"
    try:
        size = float(size_bytes)
    except (TypeError, ValueError):
        return "-"
    if size < 1024:
        return f"{int(size)} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"


def _styled_table(rows, col_widths, header: bool = False) -> Table:
    table = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style_commands = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2a3a")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d4e6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style_commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#244b7a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
        data_start = 1
    else:
        data_start = 0
    if len(rows) > data_start:
        style_commands.append(
            ("ROWBACKGROUNDS", (0, data_start), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")])
        )
        style_commands.append(("FONTNAME", (0, data_start), (0, -1), "Helvetica-Bold"))
        style_commands.append(("TEXTCOLOR", (0, data_start), (0, -1), colors.HexColor("#244b7a")))
    table.setStyle(TableStyle(style_commands))
    return table
