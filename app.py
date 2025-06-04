from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
import detection.face_capture as face_capture
import detection.intruder_detection as intruder_detection
import detection.remote_logs_server as remote_logs_server
import detection.train_model as train_model
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)

# -------------------- USER DATA HANDLING --------------------

USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        # Create admin user if file doesn’t exist
        with open(USERS_FILE, 'w') as f:
            json.dump({"admin": "1234"}, f, indent=4)
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Load users at startup
registered_users = load_users()

# -------------------- ROUTES --------------------

@app.route('/')
def home():
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
    # Replace with actual face recognition
    result = intruder_detection.recognize_face()
    if result == "success":
        session.permanent = True
        session['user'] = 'face_user'
        return jsonify(status="success")
    else:
        return jsonify(status="fail", message="Face not recognized")

@app.route('/index')
def index():
    if 'user' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Backend features
@app.route('/register-face')
def register_face():
    username = request.args.get('username')
    if not username:
        return "Username is required to register face.", 400
    face_capture.capture_faces(username)
    return f"Face capture completed for {username}."

@app.route('/train-model')
def train_face_model():
    train_model.train_model()
    return "Training completed."

@app.route('/start-detection')
def start_detection():
    intruder_detection.detect_intruder()
    return "Detection started."

# New: JSON API endpoint to return logs data for frontend dynamic loading
@app.route('/logs')
def logs():
    images = remote_logs_server.get_sorted_files_with_timestamps(remote_logs_server.INTRUDER_IMAGES_DIR)
    recordings = remote_logs_server.get_sorted_files_with_timestamps(remote_logs_server.SCREEN_RECORDINGS_DIR)

    images_json = [(fn, ts.strftime("%Y-%m-%d %H:%M:%S")) for fn, ts in images]
    recordings_json = [(fn, ts.strftime("%Y-%m-%d %H:%M:%S")) for fn, ts in recordings]

    return jsonify({
        "images": images_json,
        "recordings": recordings_json
    })

# -------------------- MAIN --------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
