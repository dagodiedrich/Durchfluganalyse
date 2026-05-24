# Durchfluganalyse

Lokale Web-App zur Erkennung von Vogel-Durchfluegen und Tier-Erscheinungen in Gartenvideos. Erkannte Ereignisse werden als einzelne Clips exportiert; pro Video wird zusaetzlich ein PDF-Bericht erstellt.

## Funktionen

- Videos aus dem Ordner `upload/` auswaehlen (Einzel- oder Mehrfachanalyse)
- Bewegungserkennung mit anpassbaren, konservativen Filterparametern
- Unterscheidung zwischen **Durchflug** und **Tier-Erscheinung**
- Clip-Export in `output/clips/Analyseclips_<Videoname>/`
- Automatische **Analysedokumentation** als PDF im gleichen Ordner
- Dashboard mit Fortschrittsanzeige, Kennzahlen und Clip-Vorschau

## Voraussetzungen

- Python 3.10 oder neuer (empfohlen: 3.11+)
- Windows, macOS oder Linux

## Installation und Start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
python launcher.py
```

Im Browser oeffnen: [http://127.0.0.1:5050](http://127.0.0.1:5050)

### Windows (Doppelklick)

`start_app.bat` legt bei Bedarf eine virtuelle Umgebung an, installiert Abhaengigkeiten und startet die App inkl. Browser.

## Nutzung

1. Video-Dateien (z. B. `.mp4`, `.mov`, `.mkv`) in den Ordner `upload/` kopieren.
2. In der App ein oder mehrere Videos per Checkbox waehlen.
3. **Analyse starten** — die Videos werden nacheinander verarbeitet.
4. Ergebnisse:
   - Clips: `output/clips/Analyseclips_<Videoname>/`
   - PDF: `Analysedokumentation_<Videoname>.pdf` im gleichen Ordner

## Parameter

Im Dashboard koennen u. a. angepasst werden:

| Parameter | Bedeutung |
|-----------|-----------|
| Min./Max. Objektflaeche | Groesse erkannte Objekte |
| Min. Geschwindigkeit | Filter gegen langsame Hintergrundbewegung |
| Min. Gesamtweg | Mindestbewegung eines Events |
| Max. Event-Dauer | Trennung Durchflug vs. laengere Erscheinung |
| Clip Vor-/Nachlauf | Sekunden vor/nach dem Event im Export |

Die Standardwerte sind konservativ gewaehlt, um Fehlalarme zu reduzieren.

## Optional: EXE bauen (Windows)

```bat
build_exe.bat
```

Die fertige Datei liegt unter `dist\VideoanalyseStarter\VideoanalyseStarter.exe`.

## Projektstruktur

```
.
├── app.py              # Flask-Server und API
├── detector.py         # Videoanalyse und Clip-Export
├── report_pdf.py       # PDF-Berichtserstellung
├── launcher.py         # Start mit automatischem Browser
├── requirements.txt
├── static/             # Frontend (CSS, JS)
├── templates/          # HTML-Dashboard
├── upload/             # Eingabe-Videos (leer im Repo)
└── output/             # Analyseergebnisse (leer im Repo)
```

## Lizenz

Siehe [LICENSE](LICENSE) — MIT-Lizenz, freie Nutzung mit Quellenangabe.
