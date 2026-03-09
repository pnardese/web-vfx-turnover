# AAF Migration: Remove Flask Server via Pyodide

Migrate AAF read/write from `server.py` (Flask + pyaaf2) to **Pyodide** running in the
browser. Goal: remove the local server dependency without reimplementing the AAF binary
format in JavaScript.

---

## Why Pyodide

pyaaf2 is **pure Python with zero external dependencies** (no C extensions, no
`Requires-Dist`). It installs via `micropip` in Pyodide without issues.

The existing `server.py` logic runs verbatim inside Pyodide — no reimplementation risk,
no AAF binary format knowledge required, markers included from day one.

| | Pyodide | cfb.js (alternative) |
|---|---|---|
| Implementation effort | Low — reuse server.py logic | High — reimplement binary format in JS |
| Avid compatibility risk | None — same code path as today | Medium (sector size differences) |
| Marker creation | Works immediately | Phase 2, high effort |
| First-load overhead | ~12 MB + ~3s init (CDN, cached) | ~200 KB, instant |

---

## What the server currently does (for reference)

1. Copy input AAF to output path (`shutil.copy2`)
2. Open with `aaf2.open(path, 'rw')`
3. Walk `CompositionMob` → video `TimelineMobSlot` → `Components` (skip `Filler`)
4. Match `SourceClip` / `Selector` / `OperationGroup` to events by sequential index
5. Write `ComponentAttributeList` (PID `0xffc8`) → `TaggedValue` objects:
   - `_COMMENT` (string) — VFX ID
   - `_COLOR_R`, `_COLOR_G`, `_COLOR_B` (uint16) — clip label colour
6. Optionally create `EventMobSlot` with `DescriptiveMarker` objects
7. `f.save()`

---

## Implementation Steps

- [x] **1. Add Pyodide CDN script to `index.html`**
  ```html
  <script src="https://cdn.jsdelivr.net/pyodide/v0.27.3/full/pyodide.js"></script>
  ```
  Add before the Babel script block.

- [x] **2. Add `initPyodide()` helper**
  Initialise once and cache the instance. Show a loading indicator in the AAF section
  while Pyodide and pyaaf2 load (first use only — subsequent calls return immediately).
  ```js
  let _pyodide = null;
  async function initPyodide() {
    if (_pyodide) return _pyodide;
    _pyodide = await loadPyodide();
    await _pyodide.loadPackage('micropip');
    await _pyodide.runPythonAsync(`
      import micropip
      await micropip.install('pyaaf2')
    `);
    return _pyodide;
  }
  ```

- [x] **3. Extract AAF processing logic from `server.py` into a Python string constant**
  Create a self-contained Python function string (no Flask, no HTTP) that accepts
  input/output paths and a JSON string of events + options, runs the pyaaf2 logic,
  and writes the output file. Keep it in a `const AAF_PYTHON_SCRIPT = \`...\`` block
  in `index.html` (plain `<script>`, not Babel).

  Signature:
  ```python
  def process_aaf(input_path, output_path, events_json, options_json):
      import aaf2, json, shutil
      events = json.loads(events_json)
      opts   = json.loads(options_json)
      shutil.copy2(input_path, output_path)
      with aaf2.open(output_path, 'rw') as f:
          # ... existing server.py logic ...
          f.save()
  ```

- [x] **4. Implement `exportAAFWithPyodide(aafArrayBuffer, events, opts)`**
  ```js
  async function exportAAFWithPyodide(aafArrayBuffer, events, opts) {
    const py = await initPyodide();

    // Write input to virtual FS
    py.FS.writeFile('/tmp/input.aaf', new Uint8Array(aafArrayBuffer));

    // Define and call the processing function
    await py.runPythonAsync(AAF_PYTHON_SCRIPT);
    await py.runPythonAsync(`
      process_aaf(
        '/tmp/input.aaf',
        '/tmp/output.aaf',
        '${JSON.stringify(events)}',
        '${JSON.stringify(opts)}'
      )
    `);

    // Read result and clean up
    const result = py.FS.readFile('/tmp/output.aaf');
    py.FS.unlink('/tmp/input.aaf');
    py.FS.unlink('/tmp/output.aaf');
    return result; // Uint8Array
  }
  ```

- [x] **5. Update `exportAAF` in `index.html`**
  Replace the `fetch('http://localhost:5000/export-aaf', ...)` block:
  ```js
  const buf  = await aafFile.arrayBuffer();
  const bytes = await exportAAFWithPyodide(buf, events, opts);
  const blob = new Blob([bytes], { type: 'application/octet-stream' });
  // trigger download as before
  ```

- [x] **6. Add Pyodide loading state to the AAF section UI**
  - Add `pyodideStatus` state: `'idle' | 'loading' | 'ready' | 'error'`
  - On first AAF file drop (or on page load if preferred): call `initPyodide()` in
    background so it's ready by the time the user clicks Export
  - Show a small status indicator (e.g. "Loading Python runtime…") while loading
  - Export button: disabled only while `pyodideStatus === 'loading'`

- [x] **7. Remove Flask server state and UI** (N/A — master branch never had it)
  - Remove `serverStatus` state and its `useEffect` health-check fetch
  - Remove server online/offline badge from the AAF section header
  - Remove `serverStatus !== 'online'` guard on the Export button
  - Update Help/Info page — remove local server launch instructions
  - `server.py`, `requirements_server.txt`, `launch.sh` can be deleted or archived
    once validated

- [x] **8. Handle JSON string escaping safely**
  The inline `JSON.stringify` approach in step 4 is fragile if values contain quotes.
  Use `py.globals.set()` to pass data instead:
  ```js
  py.globals.set('events_json', JSON.stringify(events));
  py.globals.set('options_json', JSON.stringify(opts));
  await py.runPythonAsync(`process_aaf('/tmp/input.aaf', '/tmp/output.aaf', events_json, options_json)`);
  ```

- [ ] **9. Validate against Avid Media Composer**
  - Input AAF + EDL → run export → open output in Avid
  - Verify clip notes (`_COMMENT`) and clip colours appear correctly
  - Verify markers if `includeMarkers` is enabled
  - Use `test/old/VFX_033_26-02-26.Copy.01_new.aaf` as ground truth

---

## Files to Modify / Remove

| File | Action |
|------|--------|
| `index.html` | Add Pyodide `<script>`, add `initPyodide` + `exportAAFWithPyodide`, update `exportAAF`, remove server state/UI |
| `server.py` | Delete after validation (or keep as reference in `test/`) |
| `requirements_server.txt` | Delete |
| `launch.sh` | Delete or simplify (no longer needs to start Flask) |

## Test Assets

- Input AAF: any Avid sequence AAF, or `test/old/VFX_033_26-02-26.Copy.01.aaf`
- Ground truth: `test/old/VFX_033_26-02-26.Copy.01_new.aaf`
- EDL: existing test files in `test/`
