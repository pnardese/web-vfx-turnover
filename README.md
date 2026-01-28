# VFX Turnover Tool v0.1

A web-based tool that streamlines VFX sequence preparation for post-production. It processes EDL files and generates multiple output formats for VFX production workflows.

## Features

- **Automatic VFX ID Generation** - Creates VFX IDs based on scene numbers (format: `FILM_ID_SCENE_SHOT`)
- **Support for Existing Markers** - Recognizes LOC lines in EDL files
- **Multiple Export Formats** - Markers, Subcaps, ALE, EDL, and spreadsheet formats
- **Timecode Calculations** - Customizable FPS and handles
- **Drag-and-Drop Interface** - Easy file upload
- **Persistent Settings** - Configuration saved locally in browser
- **Incoming VFX EDL** - Match VFX vendor clips to original EDL by source timecodes

## Usage

### 1. Configure Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Film ID | Project identifier used in VFX IDs | FILM_ID |
| FPS | Frame rate for timecode calculations | 24 |
| Handles | Extra frames added to pulls | 10 |

### 2. Upload EDL

Drag & drop or click to browse for an `.edl` file. The tool will parse the EDL and display events in a preview table.

- **Green VFX IDs** = Existing markers from LOC lines
- **Gray VFX IDs** = Auto-generated from scene numbers

### 3. Export Files

| Export | Description |
|--------|-------------|
| **Markers** | AVID timeline markers (configurable user, track V1-V8, and color) |
| **Subcaps** | Subtitle format for burn-ins |
| **ALE Pulls** | Avid Log Exchange file with handles for creating pulls |
| **Pulls EDL** | EDL for cutting in VFX pulls |
| **Google Tab** | Tab-delimited file for spreadsheet import |

### 4. Incoming VFX EDL

For integrating rendered VFX back into your timeline:

1. Upload an AVID Bin export file (`.txt`) containing the VFX vendor's clip names
2. The tool matches clips by source timecodes
3. Export the incoming EDL for conforming

## Supported File Formats

| Type | Extensions |
|------|------------|
| EDL Input | `.edl` |
| AVID Bin | `.txt` |

## Technology

Single-page web application built with:
- React 18
- Tailwind CSS
- No server required - runs entirely in the browser

## Installation

No installation required. Simply open `index.html` in a web browser.

Alternatively, host on any static web server.

## Contact

For questions or feedback: [pnardese@gmail.com](mailto:pnardese@gmail.com)

## License

MIT License
