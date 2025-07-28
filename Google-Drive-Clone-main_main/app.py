from flask import Flask, render_template, request, jsonify, redirect, session, send_from_directory
import os
import cv2
import numpy as np
from datetime import datetime
import pickle
import shutil
import sys
sys.path.append(r"C:\Users\TANISHQ JOSHI\Desktop\IDS")  
import intruder_detection


app = Flask(__name__)
app.secret_key = "your_secret_key"

# Folder paths
IDS_FOLDER = r"C:\Users\arnav\Desktop\IDS"  # <-- CHANGE this if your IDS is in another folder
INTRUDER_FOLDER = "static/intruders"
UPLOAD_FOLDER = "uploaded_files"
os.makedirs(INTRUDER_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------ Home Page ------------------
@app.route("/")
def home():
    return render_template("login.html")

# ------------------ Drive Dashboard ------------------
@app.route("/index")
def index():
    return render_template("index.html")

# ------------------ Password Login ------------------
@app.route("/password-login", methods=["POST"])
def password_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not os.path.exists("users.txt"):
        return jsonify({"status": "fail", "message": "No users registered."})

    with open("users.txt", "r") as f:
        for line in f:
            saved_user, saved_pass = line.strip().split(":")
            if saved_user == username and saved_pass == password:
                session["username"] = username
                return jsonify({"status": "success", "message": "Login successful"})

    return jsonify({"status": "fail", "message": "Invalid credentials"})

# ------------------ Register New User ------------------
@app.route("/register-user", methods=["POST"])
def register_user():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"status": "fail", "message": "Username and password are required."})

    with open("users.txt", "a") as f:
        f.write(f"{username}:{password}\n")

    return jsonify({"status": "success", "message": "User registered successfully!"})

# ------------------ Face Recognition Login ------------------
@app.route('/face-login', methods=['POST'])
def face_login():
    recognized_user = intruder_detection.recognize_face()
    if recognized_user != "fail":
        session.permanent = True
        session['user'] = recognized_user
        return jsonify(status="success", username=recognized_user)
    else:
        return jsonify(status="fail", message="Face not recognized")



# ------------------ Upload File ------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    folder = request.form.get("folder", "")
    folder_path = os.path.join(UPLOAD_FOLDER, folder)
    os.makedirs(folder_path, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "fail", "message": "No file part in request."})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "fail", "message": "No selected file."})

    file_path = os.path.join(folder_path, file.filename)
    file.save(file_path)
    return jsonify({"status": "success", "message": f"File '{file.filename}' uploaded successfully."})

# ------------------ List Files and Folders ------------------
@app.route("/list-files", methods=["GET"])
def list_files():
    folder = request.args.get("folder", "")
    folder_path = os.path.join(UPLOAD_FOLDER, folder)
    if not os.path.exists(folder_path):
        return jsonify({"status": "fail", "message": "Folder not found."})

    items = []
    for entry in os.listdir(folder_path):
        full_path = os.path.join(folder_path, entry)
        if os.path.isdir(full_path):
            items.append({"name": entry, "type": "folder"})
        else:
            items.append({"name": entry, "type": "file"})

    return jsonify({"status": "success", "items": items})

# ------------------ Delete File or Folder ------------------
@app.route("/delete", methods=["POST"])
def delete_item():
    data = request.get_json()
    folder = data.get("folder", "")
    name = data.get("name")
    if not name:
        return jsonify({"status": "fail", "message": "Name is required."})

    path = os.path.join(UPLOAD_FOLDER, folder, name)
    if not os.path.exists(path):
        return jsonify({"status": "fail", "message": "File/folder not found."})

    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return jsonify({"status": "success", "message": f"'{name}' deleted successfully."})
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)})

# ------------------ Rename File or Folder ------------------
@app.route("/rename", methods=["POST"])
def rename_item():
    data = request.get_json()
    folder = data.get("folder", "")
    old_name = data.get("old_name")
    new_name = data.get("new_name")

    if not old_name or not new_name:
        return jsonify({"status": "fail", "message": "Old name and new name are required."})

    old_path = os.path.join(UPLOAD_FOLDER, folder, old_name)
    new_path = os.path.join(UPLOAD_FOLDER, folder, new_name)

    if not os.path.exists(old_path):
        return jsonify({"status": "fail", "message": "Original file/folder not found."})

    if os.path.exists(new_path):
        return jsonify({"status": "fail", "message": "New file/folder name already exists."})

    try:
        os.rename(old_path, new_path)
        return jsonify({"status": "success", "message": f"Renamed '{old_name}' to '{new_name}' successfully."})
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)})

# ------------------ Serve Uploaded Files ------------------
@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ------------------ Logout ------------------
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")

# ------------------ Run Flask App ------------------
if __name__ == "__main__":
    app.run(debug=True)
