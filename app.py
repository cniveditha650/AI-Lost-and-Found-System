"""
============================================================
  AI-Based Lost & Found System
  Dataset: Delhi Metro Lost and Found (Kaggle)
  kaggle.com/datasets/forgetabhi/delhi-metro-lost-and-found-dataset
============================================================
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import os, uuid, json
import numpy as np
from PIL import Image
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs('uploads', exist_ok=True)

DB_FILE = 'database.json'

# ── DB helpers ────────────────────────────────────────────────
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"items": []}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ── Image AI ──────────────────────────────────────────────────
def extract_features(image_path):
    """Color histogram feature vector (96-dim) from an image."""
    try:
        img = Image.open(image_path).convert('RGB').resize((64, 64))
        arr = np.array(img)
        feats = []
        for ch in range(3):
            hist, _ = np.histogram(arr[:, :, ch], bins=32, range=(0, 256))
            feats.extend((hist / (hist.sum() + 1e-9)).tolist())
        return feats
    except:
        return None

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0

def find_image_matches(query_feats, query_type, threshold=0.78):
    db = load_db()
    opposite = 'found' if query_type == 'lost' else 'lost'
    results = []
    for item in db['items']:
        if item['type'] == opposite and item.get('features'):
            score = cosine_similarity(query_feats, item['features'])
            if score >= threshold:
                results.append({**{k: v for k, v in item.items() if k != 'features'},
                                 'similarity_score': round(score * 100, 1)})
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    return results[:10]

def find_text_matches(category, description, query_type):
    """Simple keyword match when no image is available."""
    db = load_db()
    opposite = 'found' if query_type == 'lost' else 'lost'
    keywords = set(description.lower().split())
    results = []
    for item in db['items']:
        if item['type'] == opposite and item['status'] == 'open':
            if item['category'] == category:
                item_words = set(item['description'].lower().split())
                overlap = len(keywords & item_words)
                if overlap >= 2:
                    results.append({**{k: v for k, v in item.items() if k != 'features'},
                                    'similarity_score': min(99, overlap * 15)})
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    return results[:10]

# ── Routes ────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report')
def report():
    return render_template('report.html')

@app.route('/browse')
def browse():
    return render_template('browse.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ── API ───────────────────────────────────────────────────────
@app.route('/api/report', methods=['POST'])
def api_report():
    try:
        item_type   = request.form.get('type', 'lost')
        name        = request.form.get('name', '').strip()
        email       = request.form.get('email', '').strip()
        category    = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        location    = request.form.get('location', '').strip()
        date        = request.form.get('date', '')

        if not all([name, email, category, description]):
            return jsonify({'error': 'Please fill all required fields'}), 400

        filename = None
        features = None
        img_file = request.files.get('image')
        if img_file and img_file.filename:
            ext = os.path.splitext(img_file.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                return jsonify({'error': 'Only JPG/PNG/WEBP images allowed'}), 400
            filename = f"{uuid.uuid4()}{ext}"
            fpath = os.path.join('uploads', filename)
            img_file.save(fpath)
            features = extract_features(fpath)

        db = load_db()
        item_id = str(uuid.uuid4())[:8].upper()
        item = {
            'id': item_id, 'type': item_type, 'name': name, 'email': email,
            'category': category, 'description': description,
            'location': location, 'date': date, 'image': filename,
            'features': features, 'status': 'open',
            'created_at': datetime.now().isoformat(), 'source': 'user'
        }
        db['items'].append(item)
        save_db(db)

        # Auto-match
        if features:
            matches = find_image_matches(features, item_type, threshold=0.78)
        else:
            matches = find_text_matches(category, description, item_type)

        return jsonify({'success': True, 'item_id': item_id,
                        'matches_found': len(matches), 'matches': matches})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        search_type = request.form.get('type', 'lost')
        img_file    = request.files.get('image')
        keyword     = request.form.get('keyword', '').strip()
        category    = request.form.get('category', '').strip()

        # Image search
        if img_file and img_file.filename:
            tmp = f"tmp_{uuid.uuid4()}.jpg"
            tpath = os.path.join('uploads', tmp)
            img_file.save(tpath)
            feats = extract_features(tpath)
            os.remove(tpath)
            if not feats:
                return jsonify({'error': 'Could not read image'}), 400
            matches = find_image_matches(feats, search_type, threshold=0.72)
            return jsonify({'success': True, 'matches': matches, 'method': 'image'})

        # Keyword / category search
        db = load_db()
        items = [i for i in db['items'] if i['status'] == 'open']
        if category:
            items = [i for i in items if i['category'] == category]
        if keyword:
            kw = keyword.lower()
            items = [i for i in items
                     if kw in i['description'].lower()
                     or kw in i['location'].lower()
                     or kw in i['category'].lower()]
        result = [{k: v for k, v in i.items() if k != 'features'} for i in items]
        result.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({'success': True, 'matches': result[:30], 'method': 'keyword'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/items', methods=['GET'])
def api_items():
    db = load_db()
    items = db['items']
    t   = request.args.get('type')
    cat = request.args.get('category')
    st  = request.args.get('status', 'open')
    src = request.args.get('source')
    if t:   items = [i for i in items if i['type'] == t]
    if cat: items = [i for i in items if i['category'] == cat]
    if st:  items = [i for i in items if i['status'] == st]
    if src: items = [i for i in items if i.get('source') == src]
    result = [{k: v for k, v in i.items() if k != 'features'} for i in items]
    result.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify({'items': result, 'total': len(result)})


@app.route('/api/items/<item_id>/resolve', methods=['POST'])
def api_resolve(item_id):
    db = load_db()
    for item in db['items']:
        if item['id'] == item_id:
            item['status'] = 'resolved'
            save_db(db)
            return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/items/<item_id>', methods=['DELETE'])
def api_delete(item_id):
    db = load_db()
    db['items'] = [i for i in db['items'] if i['id'] != item_id]
    save_db(db)
    return jsonify({'success': True})


@app.route('/api/stats')
def api_stats():
    db = load_db()
    items = db['items']
    cats = {}
    for i in items:
        cats[i['category']] = cats.get(i['category'], 0) + 1
    return jsonify({
        'total':    len(items),
        'lost':     sum(1 for i in items if i['type'] == 'lost'),
        'found':    sum(1 for i in items if i['type'] == 'found'),
        'resolved': sum(1 for i in items if i['status'] == 'resolved'),
        'open':     sum(1 for i in items if i['status'] == 'open'),
        'by_category': cats,
        'dataset_records': sum(1 for i in items if i.get('source') == 'delhi_metro'),
    })


if __name__ == '__main__':
    print("=" * 50)
    print("  AI Lost & Found System")
    print("  Dataset: Delhi Metro Lost & Found (Kaggle)")
    print("=" * 50)
    print("  Open: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True)
