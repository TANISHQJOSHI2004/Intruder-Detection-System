import cv2
import os
import json
import datetime
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from twilio.rest import Client

# Base directories
BASE_DIR = os.path.join(os.path.expanduser("~/Desktop"), "IDS")
MODEL_PATH = os.path.join(BASE_DIR, "face_model.yml")
LABEL_MAPPING_PATH = os.path.join(BASE_DIR, "label_mapping.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
INTRUDER_IMAGES_DIR = os.path.join(LOG_DIR, "intruder_images")
os.makedirs(INTRUDER_IMAGES_DIR, exist_ok=True)

# Load the model and label mapping
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
if not os.path.exists(LABEL_MAPPING_PATH):
    raise FileNotFoundError(f"Label mapping file not found: {LABEL_MAPPING_PATH}")

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

with open(LABEL_MAPPING_PATH, "r") as file:
    label_dict = json.load(file)

# Haarcascade for face detection
HAARCASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
if not os.path.exists(HAARCASCADE_PATH):
    raise FileNotFoundError(f"Haarcascade file not found: {HAARCASCADE_PATH}")
face_cascade = cv2.CascadeClassifier(HAARCASCADE_PATH)

# Email Configuration
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "akshatkansara07@gmail.com")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "arnavkansara3@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "micibwqzsngiudek")

# Twilio WhatsApp Configuration
ACCOUNT_SID = "ACf8fc70a665f1a5eb8c7ceb9d2ec44b3d"
AUTH_TOKEN = "94271ba3ab62001cf8f596a20bbd727b"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
RECIPIENT_WHATSAPP_NUMBER = "whatsapp:+919638800270"

# Cooldown configuration
last_alert_time = {}
ALERT_COOLDOWN = 30  # seconds

def send_email(subject, body, attachment_path=None):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path:
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
        msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_whatsapp_message(image_path, message_body):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    image_host_url = "https://your_public_hosting_url.com/" + os.path.basename(image_path)  # TODO: Replace with your actual URL
    try:
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=RECIPIENT_WHATSAPP_NUMBER,
            media_url=[image_host_url]
        )
        print(f"✅ WhatsApp message sent: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")

def save_intruder_image(frame):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    intruder_image_path = os.path.join(INTRUDER_IMAGES_DIR, f"intruder_{timestamp}.jpg")
    cv2.imwrite(intruder_image_path, frame)
    return intruder_image_path

def handle_intruder(face_id, frame):
    global last_alert_time
    current_time = time.time()

    if face_id in last_alert_time and current_time - last_alert_time[face_id] < ALERT_COOLDOWN:
        print(f"⚠️ Cooldown active for face {face_id}. Skipping alert.")
        return

    last_alert_time[face_id] = current_time
    print(f"🚨 Intruder detected! Face ID: {face_id}")
    intruder_image_path = save_intruder_image(frame)

    send_email(
        subject=f"Intruder Alert: Face ID {face_id}",
        body="An unauthorized person has been detected. See the attached image for details.",
        attachment_path=intruder_image_path
    )

    send_whatsapp_message(
        image_path=intruder_image_path,
        message_body="⚠️ Alert! An intruder has been detected. See the attached image."
    )

def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    print(f"👀 Detected {len(faces)} face(s) in the frame.")

    for face_id, (x, y, w, h) in enumerate(faces):
        face = gray[y:y+h, x:x+w]

        try:
            label, confidence = recognizer.predict(face)
            print(f"🧠 Prediction — Label: {label}, Confidence: {confidence:.2f}")
        except:
            print("⚠️ Prediction failed. Skipping face.")
            continue

        if confidence < 80:  # Relaxed threshold
            user_name = label_dict.get(str(label), "Unknown")
            print(f"✅ Recognized: {user_name} (Face ID: {face_id}, Confidence: {confidence:.2f})")
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{user_name} ({confidence:.2f})", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        else:
            print(f"🚨 Unrecognized face detected (Face ID: {face_id})")
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(frame, "Intruder", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            handle_intruder(face_id, frame)

    return frame

def detect_intruder():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Failed to open webcam.")
        return

    print("📹 Starting intruder detection... Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame from webcam.")
            break

        processed_frame = process_frame(frame)
        cv2.imshow("Intruder Detection", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("🛑 Stopping detection...")
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    print("✅ Module intruder_detection loaded successfully.")

import cv2
import os
import json

BASE_DIR = os.path.join(os.path.expanduser("~/Desktop"), "IDS")
MODEL_PATH = os.path.join(BASE_DIR, "face_model.yml")
LABEL_MAPPING_PATH = os.path.join(BASE_DIR, "label_mapping.json")

def recognize_face():
    """
    Recognizes a face from the webcam using the trained model.
    Returns 'success' if recognized, else 'fail'.
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABEL_MAPPING_PATH):
        print("Model or label file not found.")
        return "fail"

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)

    with open(LABEL_MAPPING_PATH, "r") as f:
        label_dict = json.load(f)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("❌ Cannot access webcam.")
        return "fail"

    print("🔍 Looking for a known face. Please look at the camera...")

    recognized = False
    attempts = 0

    while attempts < 50:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            try:
                label, confidence = recognizer.predict(face)
            except:
                continue

            if confidence < 80:
                user_name = label_dict.get(str(label), "Unknown")
                print(f"✅ Recognized as {user_name} (Confidence: {confidence:.2f})")
                recognized = True
                break

        if recognized:
            break

        attempts += 1

    cam.release()
    cv2.destroyAllWindows()

    return "success" if recognized else "fail"
