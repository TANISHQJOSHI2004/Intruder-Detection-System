from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory, abort
from datetime import timedelta, datetime
import face_capture
import intruder_detection
import train_model
import json
import os
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)

# -------------- USERS FILE HANDLING --------------
USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({"admin": "1234"}, f, indent=4)
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

registered_users = load_users()

# -------------- AUTH HELPERS --------------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -------------- INTRUDER LOGS DIRECTORIES --------------
BASE_DIR = r"C:\Users\TANISHQ JOSHI\Desktop\IDS\datasets"
INTRUDER_IMAGES_DIR = os.path.join(BASE_DIR, "intruder_images")
SCREEN_RECORDINGS_DIR = os.path.join(BASE_DIR, "screen_recordings")

os.makedirs(INTRUDER_IMAGES_DIR, exist_ok=True)
os.makedirs(SCREEN_RECORDINGS_DIR, exist_ok=True)

def get_sorted_files_with_timestamps(folder):
    files_with_timestamps = []
    for root, dirs, files in os.walk(folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path):
                try:
                    name_part = os.path.splitext(filename)[0]
                    # Fixed regex to match your intruder_detection.py timestamp format
                    match = re.search(r'(\d{8}_\d{6})', name_part)
                    if match:
                        timestamp_str = match.group(1)
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        # Get relative path from folder, includes username subfolder if any
                        relative_path = os.path.relpath(file_path, folder)
                        # Replace backslashes for URLs
                        relative_path = relative_path.replace('\\', '/')
                        files_with_timestamps.append((relative_path, timestamp))
                except Exception as e:
                    print(f"Skipping {filename} due to timestamp parse error: {e}")
                    continue
    return sorted(files_with_timestamps, key=lambda x: x[1], reverse=True)

# -------------- ROUTES --------------
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('index'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register-user', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify(status="fail", message="Username and password are required.")
    if username in registered_users:
        return jsonify(status="fail", message="Username already exists.")
    registered_users[username] = password
    save_users(registered_users)
    return jsonify(status="success", message="User registered successfully.")

@app.route('/password-login', methods=['POST'])
def password_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if registered_users.get(username) == password:
        session.permanent = True
        session['user'] = username
        return jsonify(status="success")
    else:
        return jsonify(status="fail", message="Invalid username or password.")

@app.route('/face-login', methods=['POST'])
def face_login():
    recognized_user = intruder_detection.recognize_face()
    if recognized_user != "fail":
        session.permanent = True
        session['user'] = recognized_user
        return jsonify(status="success", username=recognized_user)
    else:
        return jsonify(status="fail", message="Face not recognized")

@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/register-face')
@login_required
def register_face():
    username = request.args.get('username')
    if not username:
        return "Username is required to register face.", 400
    face_capture.capture_faces(username)
    return f"Face capture completed for {username}."

@app.route('/train-model')
@login_required
def train_face_model():
    train_model.train_model()
    return "Training completed."

@app.route('/start-detection')
@login_required
def start_detection():
    intruder_detection.detect_intruder()
    return "Detection started."

# Logs API
@app.route('/logs')
@login_required
def logs():
    images = get_sorted_files_with_timestamps(INTRUDER_IMAGES_DIR)
    recordings = get_sorted_files_with_timestamps(SCREEN_RECORDINGS_DIR)
    images_json = [(fn, ts.strftime("%Y-%m-%d %H:%M:%S")) for fn, ts in images]
    recordings_json = [(fn, ts.strftime("%Y-%m-%d %H:%M:%S")) for fn, ts in recordings]
    return jsonify({
        "images": images_json,
        "recordings": recordings_json
    })

# Serve intruder images for view and download
@app.route('/view/images/<path:filename>')
@login_required
def view_image(filename):
    return send_from_directory(INTRUDER_IMAGES_DIR, filename)

@app.route('/download/images/<path:filename>')
@login_required
def download_image(filename):
    return send_from_directory(INTRUDER_IMAGES_DIR, filename, as_attachment=True)

# Serve screen recordings for view and download
@app.route('/view/recordings/<path:filename>')
@login_required
def view_recording(filename):
    return send_from_directory(SCREEN_RECORDINGS_DIR, filename)

@app.route('/download/recordings/<path:filename>')
@login_required
def download_recording(filename):
    return send_from_directory(SCREEN_RECORDINGS_DIR, filename, as_attachment=True)

# -------------- MAIN --------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
