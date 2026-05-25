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

### macOS

Im Terminal im Projektordner:

```bash
chmod +x start_app.sh build_mac.sh
./start_app.sh
```

Optional eine eigenstaendige App bauen:

```bash
./build_mac.sh
```

Die App liegt danach unter `dist/Durchfluganalyse.app`.

## Fehlerbehebung: „templates/static nicht verfuegbar“

Dieser Fehler tritt auf, wenn **nicht das komplette Projekt** vorliegt (z. B. nur `app.py` kopiert) oder der Start aus einem falschen Ordner erfolgt.

1. Repository vollstaendig klonen oder ZIP entpacken — es muessen u. a. `templates/` und `static/` neben `app.py` liegen.
2. Pruefung: `python check_setup.py` (meldet fehlende Ordner/Dateien).
3. Start nur ueber `start_app.bat`, `./start_app.sh` oder `python launcher.py` **im Projektordner**.
4. Bei einer selbst gebauten EXE/App: neu bauen mit `build_exe.bat` (Windows) bzw. `build_mac.sh` (macOS).

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

## Optional: Standalone-Build

| Plattform | Skript | Ergebnis |
|-----------|--------|----------|
| Windows | `build_exe.bat` | `dist\VideoanalyseStarter\VideoanalyseStarter.exe` |
| macOS | `build_mac.sh` | `dist/Durchfluganalyse.app` |

## Projektstruktur

```
.
├── app.py              # Flask-Server und API
├── detector.py         # Videoanalyse und Clip-Export
├── report_pdf.py       # PDF-Berichtserstellung
├── launcher.py         # Start mit automatischem Browser
├── start_app.bat       # Windows-Starter
├── start_app.sh        # macOS-Starter
├── check_setup.py      # Prueft vollstaendige Installation
├── requirements.txt
├── static/             # Frontend (CSS, JS)
├── templates/          # HTML-Dashboard
├── upload/             # Eingabe-Videos (leer im Repo)
└── output/             # Analyseergebnisse (leer im Repo)
```

## Lizenz

Siehe [LICENSE](LICENSE) — MIT-Lizenz, freie Nutzung mit Quellenangabe.
