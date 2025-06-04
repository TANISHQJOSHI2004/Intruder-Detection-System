from flask import Flask, send_from_directory, render_template, abort
import os
from datetime import datetime
import re

app = Flask(__name__)

# Update this to your correct base path for logs:
BASE_DIR = r"C:\Users\TANISHQ JOSHI\Desktop\IDS\datasets"
INTRUDER_IMAGES_DIR = os.path.join(BASE_DIR, "intruder_images")
SCREEN_RECORDINGS_DIR = os.path.join(BASE_DIR, "screen_recordings")

# Ensure directories exist
os.makedirs(INTRUDER_IMAGES_DIR, exist_ok=True)
os.makedirs(SCREEN_RECORDINGS_DIR, exist_ok=True)

def get_sorted_files_with_timestamps(folder):
    """
    Recursively scan all files in folder and subfolders,
    extract timestamps from filenames, and return a sorted list of
    (relative_path, timestamp) tuples, newest first.
    """
    files_with_timestamps = []
    for root, dirs, files in os.walk(folder):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path):
                try:
                    name_part = os.path.splitext(filename)[0]
                    # Improved parsing: look for YYYYMMDD_HHMMSS_microseconds anywhere in filename
                    match = re.search(r'(\d{8}_\d{6}_\d+)', name_part)
                    if match:
                        timestamp_str = match.group(1)
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S_%f")
                        # Get relative path from folder, includes username subfolder
                        relative_path = os.path.relpath(file_path, folder)
                        files_with_timestamps.append((relative_path, timestamp))
                except Exception as e:
                    print(f"Skipping {filename} due to timestamp parse error: {e}")
                    continue
    # Sort newest first
    return sorted(files_with_timestamps, key=lambda x: x[1], reverse=True)

@app.route("/")
def home():
    try:
        intruder_images = get_sorted_files_with_timestamps(INTRUDER_IMAGES_DIR)
        screen_recordings = get_sorted_files_with_timestamps(SCREEN_RECORDINGS_DIR)
    except FileNotFoundError:
        intruder_images = []
        screen_recordings = []

    return render_template("index.html", 
                           images=intruder_images, 
                           recordings=screen_recordings)

@app.route("/view/<log_type>/<path:filename>")
def view_log(log_type, filename):
    """
    Serves the requested log file for viewing.
    Note: <path:filename> allows slashes for subfolders.
    """
    folder = None
    if log_type == "images":
        folder = INTRUDER_IMAGES_DIR
    elif log_type == "recordings":
        folder = SCREEN_RECORDINGS_DIR
    else:
        abort(404)

    # Normalize and prevent path traversal
    safe_path = os.path.normpath(filename)
    if '..' in safe_path or safe_path.startswith(os.sep):
        abort(404)

    full_path = os.path.join(folder, safe_path)
    if os.path.exists(full_path):
        directory = os.path.dirname(full_path)
        file_name = os.path.basename(full_path)
        return send_from_directory(directory, file_name)
    else:
        abort(404)

@app.route("/download/<log_type>/<path:filename>")
def download_log(log_type, filename):
    """
    Serves the requested log file for download.
    """
    folder = None
    if log_type == "images":
        folder = INTRUDER_IMAGES_DIR
    elif log_type == "recordings":
        folder = SCREEN_RECORDINGS_DIR
    else:
        abort(404)

    safe_path = os.path.normpath(filename)
    if '..' in safe_path or safe_path.startswith(os.sep):
        abort(404)

    full_path = os.path.join(folder, safe_path)
    if os.path.exists(full_path):
        directory = os.path.dirname(full_path)
        file_name = os.path.basename(full_path)
        return send_from_directory(directory, file_name, as_attachment=True)
    else:
        abort(404)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
