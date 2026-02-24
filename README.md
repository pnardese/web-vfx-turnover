# VFX Turnover Tool v0.1

A web-based tool that streamlines VFX sequence preparation for post-production workflows in Avid Media Composer. It processes EDL files and generates multiple output formats for VFX production workflows.

## Features

- **Automatic VFX ID Generation** - Creates VFX IDs based on scene numbers (format: `FILM_ID_SCENE_SHOT`)
- **Support for Existing Markers** - Recognizes LOC lines in EDL files
- **Multiple Export Formats** - Markers, Subcaps, ALE, EDL, spreadsheet, and AAF clip notes
- **AAF Clip Notes** - Copies source AAF and writes VFX IDs as clip notes and timeline markers; track auto-detected; optional clip color (32 Avid colors); output saved as `_new.aaf` (requires local Python server)
- **Collapsible Config Panels** - Markers and AAF Clip Notes buttons expand their settings panel on click; collapsed by default for a clean interface
- **Timecode Calculations** - Customizable FPS and handles
- **Drag-and-Drop Interface** - Easy file upload
- **Persistent Settings** - Configuration saved locally in browser
- **Persistent File Data** - Loaded EDL and AVID Bin files are preserved across browser sessions
- **Clear Data Controls** - Easily clear loaded files with one-click buttons
- **Change Tracking** - Compare new EDL with cached version: new VFX IDs in green, removed in red
- **Incoming VFX EDL** - Match VFX vendor clips to original EDL by source timecodes

## Workflow Guide

### 1. Create EDL from Avid

Create an EDL (File_129 or CMX3600) from the Avid video track containing only shots planned for VFX. In List Options in Avid, check: **Clip Names**, **Source File Name**, and **Markers**.

VFX IDs are created automatically based on the following rule: `FILE_ID_Scene_num`, where num is a progressive number like 010, 020, 030, etc.

Existing markers on timeline are imported into the tool as existing VFX IDs (you can find them in the EDL as `*LOC/*` LOC lines). Therefore, if you add VFX shots in Avid, you need to add markers with their newly created VFX IDs to re-import them correctly into the tool.

![Configuration of the list tool in Avid Media Composer for EDL exporting](imgs/01_create_edl.png)

### 2. Export Markers and Subcaps

Click **Markers** to expand the config panel. Set user, track, color, and marker position (start or middle of clip), then click **Download**. Click **Subcaps** to export subtitle-format burn-ins directly.

### 3. Export AAF with Clip Notes

As an alternative to markers, VFX IDs can be embedded directly as clip notes in the Avid sequence AAF. Export the sequence as AAF from Avid, then click **Export AAF with VFX IDs** to open the config panel. Drop the AAF file, set user, marker color, marker position, and optionally a clip color, then click **Export**. The video track is auto-detected from the AAF. Both clip notes and timeline markers are written; the output is saved as `<name>_new.aaf`. Requires the local Python server (see Installation).

The **Clip color** dropdown lists all 32 Avid clip colors with a color swatch and name. Selecting a color writes `_COLOR_R/G/B` tagged values on each clip in the AAF, matching the format Avid uses natively.

### 4. Export Frames

Export markers from Avid as JPGs to use them to build a VFX Shots database.

![Export settings for frame extraction at marker's position](imgs/02_export_frames.png)

### 5. Export TAB Text Files

Export TAB text files with VFX IDs info, that can be imported in any database/spreadsheet to build a VFX shot database.

The exported file contains one row per shot with the following columns:

| Column | Description |
|--------|-------------|
| `#` | Shot counter |
| `Name` | VFX ID |
| `Frame` | *(empty — for thumbnail reference)* |
| `Comments` | *(empty)* |
| `Status` | *(empty)* |
| `Date` | *(empty)* |
| `Duration` | Source clip duration as timecode |
| `Start` | Source start timecode |
| `End` | Source end timecode |
| `Frame Count Duration` | Duration in frames |
| `Handles` | Handle frames configured for the project |
| `Tape` | Source reel / tape name |

### 6. Export ALE Pulls

Export ALE Pulls to create pulls (subclips with VFX IDs as names from the master clips). After selecting master clips in bin, drag ALE file on bin. Import settings: *Merge events with known sources and automatically create subclips*

![Import settings](imgs/03_merge_events_ale.png)

### 7. Export Pulls EDL

Export Pulls EDL to create a timeline with the pull subclips. Import the EDL into Avid bin, relink to the pull subclips using Names.

![Relink configuration](imgs/04_relink_edl_pulls_v02.png)

### 8. VFX Cut-ins

When you receive incoming VFX (.mov files), you can import them into Avid, export the bin in TAB format to create an EDL for cutting in the VFX into the timeline. Columns: **Color**, **Name**, **Duration**, **Start**, **End**, **Tape**.

![Columns to export from Avid bin as TAB text file](imgs/05_vfx_cutins.png)

## Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Film ID | Project identifier used in VFX IDs | FILM_ID |
| FPS | Frame rate for timecode calculations | 24 |
| Handles | Extra frames added to pulls | 10 |

## Data Persistence

All settings and loaded file data are automatically saved to your browser's local storage:

- **Settings** - Film ID, FPS, Handles, Marker User, Position, Track, and Color
- **Loaded Files** - EDL and AVID Bin file data persist across browser sessions
- **File Names** - The names of loaded files are displayed in the upload zones and preview sections

Use the clear buttons (X) next to the upload zones to remove loaded file data.

## Change Tracking

When loading a new EDL file, the tool compares it with the previously cached version:

- **Grey (unchanged)** - VFX IDs present in both versions
- **Green (new)** - VFX IDs added in the new EDL
- **Red with strikethrough (removed)** - VFX IDs no longer present in the new EDL

Removed VFX IDs are shown for reference but are excluded from all exports.

## Export Options

| Export | Description |
|--------|-------------|
| **Markers** | AVID timeline markers — click to expand config panel (user, track V1–V8, color, position start/middle) |
| **AAF Clip Notes** | Copies the source AAF, writes VFX IDs as clip notes and markers, track auto-detected — click to expand config panel (user, marker color, position, clip color); output `_new.aaf`; requires local Python server |
| **Subcaps** | Subtitle format for burn-ins |
| **Pulls ALE** | Avid Log Exchange file with handles for creating pulls |
| **Pulls EDL** | EDL for cutting in VFX pulls |
| **DB Export** | Tab-delimited file for spreadsheet / database import |

## Supported File Formats

| Type | Extensions |
|------|------------|
| EDL Input | `.edl` (File_129, CMX3600) |
| AVID Bin | `.txt` |
| AAF | `.aaf` (source sequence from Avid) |

## Technology

- **Web app** — single-page application (React 18, Tailwind CSS), runs entirely in the browser with no build step
- **AAF server** — small Flask microservice (`server.py`) required only for the AAF Clip Notes export; uses [pyaaf2](https://github.com/markreidvfx/pyaaf2) to write into Avid AAF binary files

## Installation

### Option 1: Online (browser-only features)

Access the tool directly at: [https://pnardese.github.io/web-vfx-turnover/](https://pnardese.github.io/web-vfx-turnover/)

All exports except AAF Clip Notes work without any installation. The AAF export requires the local Python server described below.

---

### Option 2: Local (full features, including AAF Clip Notes)

**Requirements:** Python 3.10+ and `git`.

#### 1. Clone the repository

```bash
git clone https://github.com/pnardese/web-vfx-turnover.git
cd web-vfx-turnover
```

#### 2. Create a Python virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements_server.txt
```

`requirements_server.txt` installs:

| Package | Purpose |
|---------|---------|
| `flask` | HTTP microservice |
| `flask-cors` | Allow browser requests from `file://` origin |
| `pyaaf2` | Read/write Avid AAF files |

#### 3. Launch

```bash
./launch.sh
```

`launch.sh` does two things:

1. Starts `server.py` in the background on **`http://localhost:5000`** (skips this step if a server is already running on that port)
2. Opens `index.html` in your default browser

The web app checks the server status on load and shows a **server online / server offline** badge next to the AAF Clip Notes section. All other exports work even when the server is offline.

#### Stopping the server

Find the server process and kill it:

```bash
lsof -ti :5000 | xargs kill
```


## Contact

For questions or feedback: [pnardese@gmail.com](mailto:pnardese@gmail.com)

## License

MIT License
