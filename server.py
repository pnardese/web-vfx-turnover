#!/usr/bin/env python3
"""
Flask microservice for VFX Turnover Tool.
Handles AAF clip notes export using pyaaf2.

Endpoint:
  POST /export-aaf  — accepts multipart (aaf_file + events JSON), returns modified AAF
  GET  /health      — liveness check for the web app
"""

from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
import aaf2
import json
import tempfile
import os
import shutil
import time
import uuid

app = Flask(__name__)
CORS(app)  # Allow requests from file:// and any local origin

MARKER_COLOR_MAP = {
    'green':   ('Green',   {'red': 13107, 'green': 52428, 'blue': 13107}),
    'red':     ('Red',     {'red': 52428, 'green': 13107, 'blue': 13107}),
    'blue':    ('Blue',    {'red': 13107, 'green': 13107, 'blue': 52428}),
    'cyan':    ('Cyan',    {'red': 13107, 'green': 52428, 'blue': 52428}),
    'magenta': ('Magenta', {'red': 52428, 'green': 13107, 'blue': 52428}),
    'yellow':  ('Yellow',  {'red': 52428, 'green': 52428, 'blue': 13107}),
    'black':   ('Black',   {'red': 0,     'green': 0,     'blue': 0}),
    'white':   ('White',   {'red': 65535, 'green': 65535, 'blue': 65535}),
}

# Maps Avid clip color name → (r16, g16, b16) for _COLOR_R/G/B TaggedValues.
# Values are 8-bit × 256. Extracted from VFX_48.Colore.aaf reference file.
CLIP_COLOR_MAP = {
    'dark blue':     (14592, 11776, 38144),
    'steel blue':    (15104, 25344, 37888),
    'dark green':    (16896, 32768, 13824),
    'cyan':          (16896, 54272, 62464),
    'teal':          (17920, 39168, 36864),
    'blue':          (22528, 17920, 58624),
    'dark grey':     (22784, 22784, 22784),
    'sky blue':      (23040, 38912, 58112),
    'green':         (25856, 50432, 21248),
    'dark purple':   (32256, 12544, 26880),
    'dark brown':    (32256, 20992, 13568),
    'olive':         (32256, 32768, 14336),
    'dark red':      (32768,  9216,  9216),
    'purple':        (36608,     0, 45824),
    'mint':          (43520, 65280, 49920),
    'crimson':       (48896,     0, 26112),
    'sand':          (48896, 43264, 36608),
    'light grey':    (48896, 48896, 48896),
    'violet':        (49408, 19200, 41216),
    'yellow-olive':  (49408, 50176, 22016),
    'brown':         (49664, 32256, 20992),
    'medium red':    (51200, 14592, 14592),
    'beige':         (56064, 55296, 47104),
    'light red':     (56832, 25600, 29696),
    'gold':          (58368, 50688,     0),
    'lavender':      (58880, 48640, 65280),
    'magenta':       (61440, 12800, 58880),
    'yellow-green':  (61952, 65280, 16384),
    'orange':        (62720, 33280, 12544),
    'pink':          (64000, 48640, 48640),
    'rose':          (65280,     0, 29440),
    'light orange':  (65280, 50176, 32768),
}


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


def _ensure_descriptive_metadata_def(f):
    """Register DescriptiveMetadata DataDef if missing.

    Avid-produced AAFs store it as 'Descriptive Metadata' (with a space), which
    pyaaf2's lookup_datadef() cannot resolve by the canonical name.
    """
    try:
        f.dictionary.lookup_datadef('DescriptiveMetadata')
    except Exception:
        dm_dd = f.create.DataDef(
            "01030201-1000-0000-060e-2b3404010101",
            "DataDef_DescriptiveMetadata",
            "Descriptive metadata",
        )
        f.dictionary.register_def(dm_dd)


def _write_aaf_clip_notes(events, input_aaf_path, output_aaf_path,
                           user='vfx', color='green', position='middle',
                           include_markers=True, clip_color='none'):
    """Copy an AAF and write VFX IDs as clip notes and optionally timeline markers.

    Mirrors json_to_aaf() in vfx_turnover.py.
    """
    color_str, color_rgb = MARKER_COLOR_MAP.get(color.lower(), MARKER_COLOR_MAP['green'])
    now_ts = int(time.time())

    shutil.copy2(input_aaf_path, output_aaf_path)

    clip_num = 0
    marker_data = []
    with aaf2.open(output_aaf_path, 'rw') as f:
        _ensure_descriptive_metadata_def(f)

        for mob in f.content.toplevel():
            video_slot = None
            for slot in mob.slots:
                if not hasattr(slot.segment, 'components'):
                    continue
                media_kind = getattr(slot, 'media_kind', None)
                if media_kind and 'picture' in str(media_kind).lower():
                    video_slot = slot
                    break

            if not video_slot:
                continue

            video_slot_id = video_slot.slot_id
            track_name = video_slot['SlotName'].value or f"V{video_slot['PhysicalTrackNumber'].value}"
            print(f'  Detected track: {track_name}')
            clip_num = 0
            timeline_pos = 0
            marker_data = []

            for comp in video_slot.segment.components:
                comp_type = type(comp).__name__
                length = getattr(comp, 'length', 0) or 0

                if comp_type == 'Filler':
                    timeline_pos += length
                    continue

                if isinstance(comp, aaf2.components.SourceClip) and comp.mob:
                    target = comp
                    clip_name = comp.mob.name
                elif comp_type == 'Selector':
                    target = comp
                    sel = comp['Selected'].value
                    clip_name = sel.mob.name if (sel and sel.mob) else ''
                elif comp_type == 'OperationGroup':
                    target = comp
                    clip_name = ''
                    segments = comp.get('InputSegments')
                    if segments:
                        for seg in segments:
                            if isinstance(seg, aaf2.components.SourceClip) and seg.mob:
                                clip_name = seg.mob.name
                                break
                            if hasattr(seg, 'components'):
                                for sc in seg.components:
                                    if isinstance(sc, aaf2.components.SourceClip) and sc.mob:
                                        clip_name = sc.mob.name
                                        break
                                if clip_name:
                                    break
                else:
                    timeline_pos += length
                    continue

                clip_num += 1

                if clip_num > len(events):
                    print(f'  Warning: more clips ({clip_num}) than events ({len(events)}), stopping')
                    break

                vfx_id = events[clip_num - 1]['VFX ID']

                # Write clip note
                attr_list = target.get('ComponentAttributeList')
                if attr_list is None:
                    target['ComponentAttributeList'] = []
                    attr_list = target['ComponentAttributeList']

                found = False
                for attr in attr_list:
                    if attr.name == '_COMMENT':
                        attr.value = vfx_id
                        found = True
                        break

                if not found:
                    tv = f.create.TaggedValue()
                    tv['Name'].value = '_COMMENT'
                    tv['Value'].value = vfx_id
                    attr_list.append(tv)

                # Write clip color
                if clip_color and clip_color != 'none' and clip_color.lower() in CLIP_COLOR_MAP:
                    r16, g16, b16 = CLIP_COLOR_MAP[clip_color.lower()]
                    color_vals = {'_COLOR_R': r16, '_COLOR_G': g16, '_COLOR_B': b16}
                    found_keys = set()
                    for attr in attr_list:
                        if attr.name in color_vals:
                            attr.value = color_vals[attr.name]
                            found_keys.add(attr.name)
                    for name, val in color_vals.items():
                        if name not in found_keys:
                            tv = f.create.TaggedValue()
                            tv['Name'].value = name
                            tv['Value'].value = val
                            attr_list.append(tv)

                if include_markers:
                    marker_frame = timeline_pos + length // 2 if position == 'middle' else timeline_pos
                    marker_data.append((marker_frame, vfx_id))

                print(f'  Clip {clip_num}: {clip_name} -> {vfx_id}' + (f'  (marker @ frame {marker_frame})' if include_markers else ''))
                timeline_pos += length

            if clip_num < len(events):
                print(f'  Warning: fewer clips ({clip_num}) than events ({len(events)})')

            if include_markers:
                # Find or create EventMobSlot for markers
                event_slot = None
                for slot in mob.slots:
                    if type(slot).__name__ == 'EventMobSlot':
                        event_slot = slot
                        break

                if event_slot is None:
                    existing_ids = {s.slot_id for s in mob.slots}
                    new_slot_id = max(existing_ids) + 1 if existing_ids else 1008
                    event_slot = f.create.EventMobSlot()
                    event_slot['SlotID'].value = new_slot_id
                    event_slot['EditRate'].value = video_slot.edit_rate
                    event_slot['SlotName'].value = ''
                    seq = f.create.Sequence(media_kind='DescriptiveMetadata')
                    seq['Components'].value = []
                    event_slot['Segment'].value = seq
                    mob.slots.append(event_slot)
                else:
                    seq = event_slot.segment

                new_markers = []
                for marker_frame, vfx_id in marker_data:
                    marker = f.create.DescriptiveMarker()
                    marker['Length'].value = 1
                    marker['Position'].value = marker_frame
                    marker['Comment'].value = vfx_id
                    marker['CommentMarkerUSer'].value = user
                    marker['CommentMarkerColor'].value = color_rgb
                    marker['DescribedSlots'].value = {video_slot_id}
                    tv_list = [
                        f.create.TaggedValue('_ATN_CRM_COLOR',            color_str),
                        f.create.TaggedValue('_ATN_CRM_COLOR_EXTENDED',   color_str),
                        f.create.TaggedValue('_ATN_CRM_USER',             user),
                        f.create.TaggedValue('_ATN_CRM_COM',              vfx_id),
                        f.create.TaggedValue('_ATN_CRM_LONG_CREATE_DATE', now_ts),
                        f.create.TaggedValue('_ATN_CRM_LONG_MOD_DATE',    now_ts),
                        f.create.TaggedValue('_ATN_CRM_LENGTH',           1),
                        f.create.TaggedValue('_ATN_CRM_ID',               uuid.uuid4().hex),
                    ]
                    marker['CommentMarkerAttributeList'].value = tv_list
                    new_markers.append(marker)

                seq['Components'].value = new_markers

        f.save()

    marker_msg = f'and {len(marker_data)} markers' if include_markers else '(no markers)'
    print(f'Added {clip_num} VFX ID clip notes {marker_msg}')
    return clip_num


@app.route('/export-aaf', methods=['POST'])
def export_aaf():
    if 'aaf_file' not in request.files:
        return jsonify({'error': 'Missing AAF file'}), 400
    if 'events' not in request.form:
        return jsonify({'error': 'Missing events data'}), 400

    aaf_file = request.files['aaf_file']

    try:
        events = json.loads(request.form['events'])
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid events JSON: {e}'}), 400

    if not events:
        return jsonify({'error': 'Events list is empty'}), 400

    include_markers = request.form.get('include_markers', 'true').lower() == 'true'
    user        = request.form.get('user',        'vfx')
    color       = request.form.get('color',       'green')
    position    = request.form.get('position',    'middle')
    clip_color  = request.form.get('clip_color',  'none')

    original_filename = aaf_file.filename or 'output.aaf'
    stem = os.path.splitext(original_filename)[0]
    download_name = f'{stem}_new.aaf'

    tmp_dir = tempfile.mkdtemp(prefix='vfx_aaf_')
    input_path = os.path.join(tmp_dir, 'input.aaf')
    output_path = os.path.join(tmp_dir, download_name)

    try:
        aaf_file.save(input_path)
        clip_count = _write_aaf_clip_notes(events, input_path, output_path, user, color, position, include_markers, clip_color)
        print(f'Serving {download_name} ({clip_count} clips annotated)')

        @after_this_request
        def cleanup(response):
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/octet-stream',
        )

    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f'Error processing AAF: {e}')
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print('VFX Turnover AAF Server')
    print('=======================')
    print('Listening on http://localhost:5000')
    print('Press Ctrl+C to stop.')
    app.run(host='localhost', port=5000, debug=False)
