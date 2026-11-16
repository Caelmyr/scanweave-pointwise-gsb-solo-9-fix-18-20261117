"""Scanning intake and provenance, independent of pixel processing workflows."""
import hashlib
import io
import json
import numpy as np
from PIL import Image, ImageDraw
from flask import request, jsonify
from . import model
from .validation import Invalid


def scanning_sample(width=720, height=480):
    """Synthetic transmission specimen: neutral border and colored detail."""
    y, x = np.indices((height, width), dtype=np.float32)
    positive = np.empty((height, width, 3), np.float32)
    positive[:, :, 0] = .12 + .75 * x / width
    positive[:, :, 1] = .1 + .75 * y / height
    positive[:, :, 2] = .3 + .2 * np.sin(x / 31)
    raster = Image.fromarray(np.uint8(np.clip(positive, 0, 1) * 255))
    draw = ImageDraw.Draw(raster)
    for i in range(9):
        left = 95 + i * 58
        draw.rectangle((left, 170, left + 42, 310), fill=(i * 27, i * 27, i * 27))
    draw.text((100, 125), 'SCANWEAVE / SYNTHETIC TRANSMISSION', fill='white')
    positive = np.asarray(raster, np.float32) / 255
    density = .2 + 1.8 * (1 - positive)
    transmission = np.power(10., -density) * np.array([.85, .52, .28])
    transmission[:32] = [.85, .52, .28]
    transmission[-32:] = [.85, .52, .28]
    transmission[:, :32] = [.85, .52, .28]
    transmission[:, -32:] = [.85, .52, .28]
    return transmission.astype(np.float32)


def manifest(store, assets, key):
    project = store.get(key)
    entries = []
    for frame in project['frames']:
        meta = assets.metadata(frame['asset'])
        entries.append({'frame_id': frame['id'], 'name': frame['name'],
                        'asset_sha256': frame['asset'], 'width': meta['width'],
                        'height': meta['height'], 'enabled': frame['enabled'],
                        'synthetic': meta.get('synthetic', False)})
    return {'schema': 'scanweave.intake.v1', 'project_id': key,
            'revision': project['revision'], 'name': project['name'],
            'notes': project['notes'], 'tags': project['tags'], 'frames': entries,
            'settings': project['settings'],
            'source_policy': 'Immutable imported samples; edits produce separate results.'}


def install(app):
    store, assets = app.extensions['store'], app.extensions['assets']

    @app.post('/api/scanner/sample')
    def sample():
        current = store.create('扫描整理 · 合成透射样张')
        image = scanning_sample()
        rng = np.random.default_rng(15)
        with store.edit(current['id'], 0, '导入合成扫描重复采样') as project:
            project['settings']['mode'] = 'denoise'
            project['settings']['size'] = 768
            project['notes'] = '合成素材，非真实胶片；四周32像素为均匀片基，内部为灰阶和彩色图案。'
            project['tags'] = ['synthetic', 'transmission', '1200dpi']
            for i in range(3):
                captured = np.clip(image + rng.normal(0, .001, image.shape), 0, 1).astype(np.float32)
                item = assets.put(captured, f'scan-repeat-{i+1}.png',
                                  {'synthetic': True, 'scanner': 'synthetic-v1', 'dpi': 1200})
                project['frames'].append(model.frame(item['id'], item['name']))
            project['reference'] = project['frames'][0]['id']
        return jsonify(store.get(current['id'])), 201

    @app.get('/api/scanner/<key>/manifest')
    def get_manifest(key):
        return jsonify(manifest(store, assets, key))

    @app.get('/api/scanner/<key>/manifest.json')
    def download_manifest(key):
        data = json.dumps(manifest(store, assets, key), ensure_ascii=False, indent=2).encode()
        from flask import Response
        return Response(data, mimetype='application/json',
                        headers={'Content-Disposition': 'attachment; filename="scan-manifest.json"'})

    @app.get('/api/scanner/<key>/integrity')
    def integrity(key):
        current = store.get(key)
        checks = [assets.verify(f['asset']) for f in current['frames']]
        return jsonify({'project_id': key, 'assets': checks,
                        'all_valid': all(c['hash_valid'] for c in checks)})
