from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
import detection.face_capture as face_capture
import detection.intruder_detection as intruder_detection
import detection.remote_logs_server as remote_logs_server
import detection.train_model as train_model

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = timedelta(minutes=30)

# In-memory user store (you can later use a database)
registered_users = {
    "admin": "1234"
}

# Redirect root to login
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return render_template('login.html')

# -------------------- AUTH ROUTES --------------------

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

# -------------------- MAIN ROUTES --------------------

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

# -------------------- BACKEND FUNCTIONALITY --------------------

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

@app.route('/logs')
def view_logs():
    logs = remote_logs_server.read_log_entries()
    return jsonify(logs)

# -------------------- MAIN --------------------

if __name__ == '__main__':
    app.run(debug=True)
