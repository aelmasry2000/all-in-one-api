from flask import Flask, render_template, request, jsonify
import PyPDF2
import os
from tinydb import TinyDB
from datetime import datetime
import json

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = TinyDB('db.json')

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_text = ''
    saved = False
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.pdf'):
            filename = file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            extracted_text = extract_text_from_pdf(filepath)
            os.remove(filepath)
        else:
            extracted_text = request.form.get('extracted_text', '')

        if 'save_metadata' in request.form:
            save_cataloging_data(
                filename=request.form.get('filename', 'unknown.pdf'),
                extracted_text=request.form.get('extracted_text', ''),
                simple_json=request.form.get('simple_json', '{}'),
                koha_json=request.form.get('koha_json', '{}'),
                marc_edit_json=request.form.get('marc_edit_json', '{}'),
                text_marc=request.form.get('text_marc', ''),
                marcxml=request.form.get('marcxml', '')
            )
            saved = True

    return render_template('index.html', extracted_text=extracted_text, saved=saved)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    query = ''
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        for record in db.all():
            record_text = json.dumps(record).lower()
            if query in record_text:
                results.append(record)
    return render_template('search.html', query=query, results=results)

@app.route('/extract', methods=['POST'])
def api_extract():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.pdf'):
        return jsonify({'error': 'No PDF file uploaded.'}), 400
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    extracted_text = extract_text_from_pdf(filepath)
    os.remove(filepath)
    return jsonify({'extracted_text': extracted_text})

@app.route('/save', methods=['POST'])
def api_save():
    data = request.json
    if not data:
        return jsonify({'error': 'No JSON data received.'}), 400

    filename = data.get('filename', 'unknown.pdf')
    extracted_text = data.get('extracted_text', '')
    json_styles = data.get('json_styles', {})
    marc_styles = data.get('marc_styles', {})

    record = {
        "filename": filename,
        "extracted_text": extracted_text,
        "json_styles": json_styles,
        "marc_styles": marc_styles,
        "timestamp": datetime.now().isoformat()
    }
    db.insert(record)
    return jsonify({'status': 'saved', 'record': record})

@app.route('/search_api', methods=['POST'])
def api_search():
    query = request.json.get('query', '').lower()
    results = []
    for record in db.all():
        record_text = json.dumps(record).lower()
        if query in record_text:
            results.append(record)
    return jsonify({'results': results})

def extract_text_from_pdf(filepath):
    text = ''
    with open(filepath, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
    return text.strip()

def save_cataloging_data(filename, extracted_text, simple_json, koha_json, marc_edit_json, text_marc, marcxml):
    try:
        record = {
            "filename": filename,
            "extracted_text": extracted_text,
            "json_styles": {
                "simple_json": json.loads(simple_json) if simple_json else {},
                "koha_json": json.loads(koha_json) if koha_json else {},
                "marc_edit_json": json.loads(marc_edit_json) if marc_edit_json else {}
            },
            "marc_styles": {
                "text_marc": text_marc,
                "xml_marc": marcxml
            },
            "timestamp": datetime.now().isoformat()
        }
        db.insert(record)
    except Exception as e:
        print(f"Error saving data: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)