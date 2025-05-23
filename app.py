from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary
from flask_migrate import Migrate
from flask_cors import CORS
from waitress import serve
import os
import json

app = Flask(__name__)
CORS(app)  # Allow React frontend requests

# Config from environment
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Association table for many-to-many MidiFile <-> Tag
file_tag = db.Table('file_tag',
    db.Column('file_id', db.Integer, db.ForeignKey('midi_file.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class MidiFile(db.Model):
    __tablename__ = 'midi_file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    file_data = db.Column(LargeBinary, nullable=False)  # binary midi data stored here
    description = db.Column(db.Text)
    tags = db.relationship('Tag', secondary=file_tag, backref='files')

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(50), unique=True, nullable=False)

# Endpoint to get list of tags
@app.route('/gettaglist', methods=['GET'])
def get_tag_list():
    tags = Tag.query.all()
    tag_list = [{'id': t.id, 'tag': t.tag} for t in tags]
    return jsonify(tag_list)

# Endpoint to add file
@app.route('/addfile', methods=['POST'])
def add_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Validate MIDI extension
    if not (file.filename.lower().endswith('.mid') or file.filename.lower().endswith('.midi')):
        return jsonify({'error': 'File must be a MIDI (.mid/.midi)'}), 400

    name = request.form.get('name')
    description = request.form.get('description')
    tags_json = request.form.get('tags', '[]')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    try:
        tag_names = json.loads(tags_json)
        if not isinstance(tag_names, list):
            raise ValueError("Tags must be a list of names")
    except Exception:
        return jsonify({'error': 'Invalid tags format'}), 400

    file_bytes = file.read()

    # Remove duplicates in a case-insensitive way, preserving original casing of first occurrence
    seen = set()
    unique_tag_names = []
    for t in tag_names:
        t_clean = t.strip()
        if not t_clean:
            continue
        t_lower = t_clean.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_tag_names.append(t_clean)

    # Create the MidiFile instance
    midi_file = MidiFile(
        name=name,
        file_data=file_bytes,
        description=description
    )

    # Process unique tag names into Tag objects (create if they don't exist)
    tags = []
    for tag_name in unique_tag_names:
        tag = Tag.query.filter_by(tag=tag_name).first()
        if not tag:
            tag = Tag(tag=tag_name)
            db.session.add(tag)
            db.session.flush()
        tags.append(tag)

    midi_file.tags = tags

    db.session.add(midi_file)
    db.session.commit()

    return jsonify({'message': 'File added successfully', 'id': midi_file.id})


# Endpoint to get files based on search filters
@app.route('/getfiles', methods=['POST'])
def get_files():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    tag_ids = data.get('tags', [])
    search = data.get('search', '').strip()

    query = MidiFile.query

    if tag_ids:
        query = query.filter(MidiFile.tags.any(Tag.id.in_(tag_ids)))

    if search:
        query = query.filter(MidiFile.name.ilike(f'%{search}%'))

    files = query.all()

    # Serialize response with tags as list of tag names only
    result = []
    for f in files:
        result.append({
            'id': f.id,
            'name': f.name,
            'description': f.description,
            'tags': [t.tag for t in f.tags]  # just tag names
        })

    return jsonify(result)


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
