import sys
import os
import cv2
import numpy as np
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QPushButton, QLabel, QMessageBox, QLineEdit, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QProgressBar
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal

# Import your existing process_frame from intruder_detection.py
from intruder_detection import process_frame


class TrainModelThread(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)  # For progress bar updates
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, dataset_dir, model_path, labels_path, augment_image_func):
        super().__init__()
        self.dataset_dir = dataset_dir
        self.model_path = model_path
        self.labels_path = labels_path
        self.augment_image = augment_image_func

    def run(self):
        try:
            self.progress.emit("Starting training...")

            if not os.path.exists(self.dataset_dir):
                raise FileNotFoundError(f"Dataset folder not found at {self.dataset_dir}")

            recognizer = cv2.face.LBPHFaceRecognizer_create()
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

            images, labels = [], []
            label_dict = {}

            user_dirs = sorted(os.listdir(self.dataset_dir))
            total_users = len(user_dirs)
            if total_users == 0:
                raise ValueError("No user folders found in dataset.")

            for idx, user_name in enumerate(user_dirs):
                user_folder = os.path.join(self.dataset_dir, user_name)
                if not os.path.isdir(user_folder):
                    continue

                self.progress.emit(f"Processing user: {user_name}")

                for filename in os.listdir(user_folder):
                    img_path = os.path.join(user_folder, filename)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        continue

                    images.append(img)
                    labels.append(idx)

                    augmented_faces = self.augment_image(img)
                    for aug_face in augmented_faces:
                        images.append(aug_face)
                        labels.append(idx)

                label_dict[str(idx)] = user_name

                percent_done = int(((idx + 1) / total_users) * 100)
                self.progress_percent.emit(percent_done)  # Update progress bar %

            if not images:
                raise ValueError(f"No images found in dataset folder: {self.dataset_dir}")

            recognizer.train(images, np.array(labels))
            recognizer.save(self.model_path)

            with open(self.labels_path, "w") as f:
                json.dump(label_dict, f, indent=4)

            self.progress.emit("Model training completed successfully.")
            self.progress_percent.emit(100)
            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Error during training: {str(e)}")


class AdvancedIntruderDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Intruder Detection System")
        self.setGeometry(100, 100, 800, 600)

        # Webcam Variables
        self.camera = None
        self.timer = QTimer()

        # Paths
        self.BASE_DIR = os.path.join(os.path.expanduser("~/Desktop"), "IDS")
        self.DATASET_DIR = os.path.join(self.BASE_DIR, "datasets")
        self.MODEL_PATH = os.path.join(self.BASE_DIR, "face_model.yml")
        self.LABELS_PATH = os.path.join(self.BASE_DIR, "label_mapping.json")

        # Main Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add Tabs
        self.tabs.addTab(self.create_home_tab(), "Home")
        self.tabs.addTab(self.create_face_management_tab(), "Face Management")
        self.tabs.addTab(self.create_logs_tab(), "Logs")
        self.tabs.addTab(self.create_settings_tab(), "Settings")

    def create_home_tab(self):
        home_tab = QWidget()
        layout = QVBoxLayout()

        self.webcam_label = QLabel("Webcam Feed")
        self.webcam_label.setAlignment(Qt.AlignCenter)
        self.webcam_label.setStyleSheet("background-color: #222; color: #fff; padding: 10px;")
        layout.addWidget(self.webcam_label)

        btn_layout = QHBoxLayout()
        start_btn = QPushButton("Start Detection")
        start_btn.clicked.connect(self.start_detection)
        btn_layout.addWidget(start_btn)

        stop_btn = QPushButton("Stop Detection")
        stop_btn.clicked.connect(self.stop_detection)
        btn_layout.addWidget(stop_btn)

        layout.addLayout(btn_layout)
        home_tab.setLayout(layout)
        return home_tab

    def create_face_management_tab(self):
        face_tab = QWidget()
        layout = QVBoxLayout()

        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("Enter New User Name")
        layout.addWidget(self.user_name_input)

        register_btn = QPushButton("Register New Face")
        register_btn.clicked.connect(self.register_new_face)
        layout.addWidget(register_btn)

        train_btn = QPushButton("Train Model")
        train_btn.clicked.connect(self.train_model)
        layout.addWidget(train_btn)

        # --- Fancy Live Status and Progress Bar ---
        self.training_status_label = QLabel("")
        self.training_status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.training_status_label)

        self.training_progress_bar = QProgressBar()
        self.training_progress_bar.setMinimum(0)
        self.training_progress_bar.setMaximum(100)
        self.training_progress_bar.setValue(0)
        layout.addWidget(self.training_progress_bar)

        face_tab.setLayout(layout)
        return face_tab

    def create_logs_tab(self):
        logs_tab = QWidget()
        layout = QVBoxLayout()

        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(2)
        self.logs_table.setHorizontalHeaderLabels(["Timestamp", "Event"])
        layout.addWidget(self.logs_table)

        refresh_btn = QPushButton("Refresh Logs")
        refresh_btn.clicked.connect(self.refresh_logs)
        layout.addWidget(refresh_btn)

        logs_tab.setLayout(layout)
        return logs_tab

    def create_settings_tab(self):
        settings_tab = QWidget()
        layout = QVBoxLayout()

        email_label = QLabel("Email Settings")
        email_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(email_label)

        test_email_btn = QPushButton("Test Email Notification")
        test_email_btn.clicked.connect(self.test_email)
        layout.addWidget(test_email_btn)

        settings_tab.setLayout(layout)
        return settings_tab

    def start_detection(self):
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            self.show_message("Error: Unable to access the webcam.")
            return

        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        self.show_message("Intruder Detection Started")

    def stop_detection(self):
        self.timer.stop()
        if self.camera and self.camera.isOpened():
            self.camera.release()
        self.webcam_label.clear()
        self.show_message("Intruder Detection Stopped")

    def update_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            self.show_message("Error: Failed to grab frame.")
            self.stop_detection()
            return

        frame = process_frame(frame)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.webcam_label.setPixmap(QPixmap.fromImage(qt_image))

    # --- Face Registration Logic integrated ---
    def sanitize_name(self, name):
        return name.strip().replace(" ", "_").lower()

    def augment_image(self, face_img):
        augmented = []
        rows, cols = face_img.shape

        for angle in [-10, 10]:
            M = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)
            rotated = cv2.warpAffine(face_img, M, (cols, rows), borderMode=cv2.BORDER_REFLECT)
            augmented.append(rotated)

        flipped = cv2.flip(face_img, 1)
        augmented.append(flipped)

        return augmented

    def register_new_face(self):
        user_name = self.user_name_input.text().strip()
        if not user_name:
            self.show_message("Please enter a valid user name.")
            return

        # Run face capture (blocking - will open window, press q to quit)
        self.capture_faces(user_name)
        self.show_message(f"Face registration completed for {user_name}.")

    def capture_faces(self, user_name):
        folder_name = self.sanitize_name(user_name)
        user_folder = os.path.join(self.DATASET_DIR, folder_name)
        os.makedirs(user_folder, exist_ok=True)

        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if not os.path.exists(face_cascade_path):
            self.show_message(f"Haarcascade not found at {face_cascade_path}")
            return

        face_cascade = cv2.CascadeClassifier(face_cascade_path)

        if not camera.isOpened():
            self.show_message("Unable to access the camera.")
            return

        count = 0
        target_images = 100

        while count < target_images:
            ret, frame = camera.read()
            if not ret:
                self.show_message("Failed to read frame from camera.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

            for (x, y, w, h) in faces:
                face = gray[y:y + h, x:x + w]
                face_resized = cv2.resize(face, (150, 150))

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"{folder_name}_{timestamp}.jpg"
                full_path = os.path.join(user_folder, filename)
                cv2.imwrite(full_path, face_resized)
                count += 1

                for aug_face in self.augment_image(face_resized):
                    aug_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    aug_filename = f"{folder_name}_{aug_timestamp}.jpg"
                    aug_path = os.path.join(user_folder, aug_filename)
                    cv2.imwrite(aug_path, aug_face)
                    count += 1

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.imshow("Face Capture - Press 'q' to quit", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        camera.release()
        cv2.destroyAllWindows()

    # --- Model Training Logic integrated ---
    def train_model(self):
        train_btn = self.sender()
        train_btn.setEnabled(False)
        self.training_status_label.setText("")
        self.training_status_label.setStyleSheet("color: green; font-weight: bold;")
        self.training_progress_bar.setValue(0)

        self.train_thread = TrainModelThread(
            self.DATASET_DIR, self.MODEL_PATH, self.LABELS_PATH, self.augment_image
        )
        self.train_thread.progress.connect(self.update_training_status)
        self.train_thread.progress_percent.connect(self.update_progress_bar)
        self.train_thread.error.connect(self.training_error)
        self.train_thread.finished.connect(lambda: train_btn.setEnabled(True))
        self.train_thread.finished.connect(self.training_finished)
        self.train_thread.start()

    def update_training_status(self, message):
        self.training_status_label.setText(message)

    def update_progress_bar(self, value):
        self.training_progress_bar.setValue(value)

    def training_error(self, message):
        self.training_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.training_status_label.setText(message)

    def training_finished(self):
        self.training_status_label.setStyleSheet("color: green; font-weight: bold;")
        self.show_message("Model training finished successfully.")
        self.training_progress_bar.setValue(100)

    def refresh_logs(self):
        logs_dir = os.path.join(self.BASE_DIR, "logs")
        log_file = os.path.join(logs_dir, "detection.log")
        if os.path.exists(log_file):
            with open(log_file, "r") as file:
                lines = file.readlines()
                self.logs_table.setRowCount(len(lines))
                for row, line in enumerate(lines):
                    if ": " in line:
                        timestamp, event = line.split(": ", 1)
                    else:
                        timestamp, event = line.strip(), ""
                    self.logs_table.setItem(row, 0, QTableWidgetItem(timestamp))
                    self.logs_table.setItem(row, 1, QTableWidgetItem(event.strip()))
        else:
            self.show_message("No logs available.")

    def test_email(self):
        self.show_message("Test Email Notification triggered.\nImplement email sending logic here.")

    def show_message(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Information")
        msg_box.setText(message)
        msg_box.exec_()


def main():
    app = QApplication([])
    window = AdvancedIntruderDetectionApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
