import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QPushButton, QLabel, QMessageBox, QLineEdit, QHBoxLayout, QTableWidget, QTableWidgetItem
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer, Qt
import cv2
import json
from .intruder_detection import process_frame  # Import face detection logic


class AdvancedIntruderDetectionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Intruder Detection System")
        self.setGeometry(100, 100, 800, 600)

        # Webcam Variables
        self.camera = None
        self.timer = QTimer()

        # Main Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add Tabs
        self.tabs.addTab(self.create_home_tab(), "Home")
        self.tabs.addTab(self.create_face_management_tab(), "Face Management")
        self.tabs.addTab(self.create_logs_tab(), "Logs")
        self.tabs.addTab(self.create_settings_tab(), "Settings")

    def create_home_tab(self):
        """
        Creates the Home tab with controls for starting detection and viewing the webcam feed.
        """
        home_tab = QWidget()
        layout = QVBoxLayout()

        # Webcam Feed Label
        self.webcam_label = QLabel("Webcam Feed")
        self.webcam_label.setAlignment(Qt.AlignCenter)
        self.webcam_label.setStyleSheet("background-color: #222; color: #fff; padding: 10px;")
        layout.addWidget(self.webcam_label)

        # Control Buttons
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
        """
        Creates the Face Management tab for registering and training faces directly in the GUI.
        """
        face_tab = QWidget()
        layout = QVBoxLayout()

        # Input for New User Name
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("Enter New User Name")
        layout.addWidget(self.user_name_input)

        # Buttons for Face Registration and Training
        register_btn = QPushButton("Register New Face")
        register_btn.clicked.connect(self.register_new_face)
        layout.addWidget(register_btn)

        train_btn = QPushButton("Train Model")
        train_btn.clicked.connect(self.train_model)
        layout.addWidget(train_btn)

        face_tab.setLayout(layout)
        return face_tab

    def create_logs_tab(self):
        """
        Creates the Logs tab to view intruder and activity logs.
        """
        logs_tab = QWidget()
        layout = QVBoxLayout()

        # Logs Table
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
        """
        Creates the Settings tab for email and WhatsApp configuration.
        """
        settings_tab = QWidget()
        layout = QVBoxLayout()

        # Email Configuration
        email_label = QLabel("Email Settings")
        email_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(email_label)

        test_email_btn = QPushButton("Test Email Notification")
        test_email_btn.clicked.connect(self.test_email)
        layout.addWidget(test_email_btn)

        # WhatsApp Configuration
        whatsapp_label = QLabel("WhatsApp Settings")
        whatsapp_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(whatsapp_label)

        test_whatsapp_btn = QPushButton("Test WhatsApp Notification")
        test_whatsapp_btn.clicked.connect(self.test_whatsapp)
        layout.addWidget(test_whatsapp_btn)

        settings_tab.setLayout(layout)
        return settings_tab

    def start_detection(self):
        """
        Starts the webcam feed and detection process.
        """
        self.camera = cv2.VideoCapture(0)  # Open webcam
        if not self.camera.isOpened():
            self.show_message("Error: Unable to access the webcam.")
            return

        # Set up a timer to fetch and display frames
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # Update every 30 ms

        self.show_message("Intruder Detection Started")

    def stop_detection(self):
        """
        Stops the webcam feed and detection process.
        """
        self.timer.stop()  # Stop the timer
        if self.camera and self.camera.isOpened():
            self.camera.release()  # Release the webcam
        self.webcam_label.clear()
        self.show_message("Intruder Detection Stopped")

    def update_frame(self):
        """
        Fetches frames from the webcam, processes them, and updates the GUI.
        """
        ret, frame = self.camera.read()
        if not ret:
            self.show_message("Error: Failed to grab frame.")
            self.stop_detection()
            return

        # Process the frame (face detection, recognition)
        frame = process_frame(frame)

        # Convert the frame to QImage and display it in the QLabel
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.webcam_label.setPixmap(QPixmap.fromImage(qt_image))

    def register_new_face(self):
        """
        Handles face registration directly in the GUI.
        """
        user_name = self.user_name_input.text().strip()
        if not user_name:
            self.show_message("Please enter a valid user name.")
            return

        # Run the face registration script
        register_script = os.path.abspath(r"C:/Users/TANISHQ JOSHI/Desktop/IDS/face_capture.py")
        if os.path.exists(register_script):
            subprocess.Popen(["python", register_script, user_name])
            self.show_message(f"Face registration started for {user_name}. Follow the prompts.")
        else:
            self.show_message(f"Script not found: {register_script}")

    def train_model(self):
        """
        Runs the model training script to update the face recognizer.
        """
        train_script = os.path.abspath(r"C:/Users/TANISHQ JOSHI/Desktop/IDS/train_model.py")
        if os.path.exists(train_script):
            subprocess.Popen(["python", train_script])
            self.show_message("Model training started. Please wait.")
        else:
            self.show_message(f"Script not found: {train_script}")

    def refresh_logs(self):
        """
        Refreshes the logs table with the latest activity.
        """
        logs_dir = os.path.join(os.path.expanduser("~/Desktop"), "IDS", "logs")
        log_file = os.path.join(logs_dir, "detection.log")
        if os.path.exists(log_file):
            with open(log_file, "r") as file:
                lines = file.readlines()
                self.logs_table.setRowCount(len(lines))
                for row, line in enumerate(lines):
                    timestamp, event = line.split(": ", 1)
                    self.logs_table.setItem(row, 0, QTableWidgetItem(timestamp))
                    self.logs_table.setItem(row, 1, QTableWidgetItem(event.strip()))
        else:
            self.show_message("No logs available.")

    def test_email(self):
        """
        Test email alert functionality.
        """
        self.show_message("Testing Email Notification...")

    def test_whatsapp(self):
        """
        Test WhatsApp notification functionality.
        """
        self.show_message("Testing WhatsApp Notification...")

    def show_message(self, message):
        """
        Displays a popup message to the user.
        """
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
