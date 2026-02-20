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

app = Flask(__name__)
CORS(app)  # Allow requests from file:// and any local origin


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


def _write_aaf_clip_notes(events, input_aaf_path, output_aaf_path):
    """Copy an AAF and write VFX IDs from events list as clip notes on each video clip.

    Adapted from json_to_aaf() in vfx_turnover.py — operates on an events list
    directly instead of reading from a JSON file.
    """
    shutil.copy2(input_aaf_path, output_aaf_path)

    clip_num = 0
    with aaf2.open(output_aaf_path, 'rw') as f:
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

            for comp in video_slot.segment.components:
                comp_type = type(comp).__name__

                if comp_type == 'Filler':
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
                    continue

                clip_num += 1

                if clip_num > len(events):
                    print(f'  Warning: more clips ({clip_num}) than events ({len(events)}), stopping')
                    break

                vfx_id = events[clip_num - 1]['VFX ID']

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
                    attr_list.append(f.create.TaggedValue('_COMMENT', vfx_id))

                print(f'  Clip {clip_num}: {clip_name} -> {vfx_id}')

            if clip_num < len(events):
                print(f'  Warning: fewer clips ({clip_num}) than events ({len(events)})')

        f.save()

    print(f'Added {clip_num} VFX ID clip notes')
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

    original_filename = aaf_file.filename or 'output.aaf'
    stem = os.path.splitext(original_filename)[0]
    download_name = f'{stem}_notes.aaf'

    tmp_dir = tempfile.mkdtemp(prefix='vfx_aaf_')
    input_path = os.path.join(tmp_dir, 'input.aaf')
    output_path = os.path.join(tmp_dir, download_name)

    try:
        aaf_file.save(input_path)
        clip_count = _write_aaf_clip_notes(events, input_path, output_path)
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
