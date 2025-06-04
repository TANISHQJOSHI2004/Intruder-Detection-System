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
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Twilio Configuration
ACCOUNT_SID = os.getenv("TWILIO_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
RECIPIENT_WHATSAPP_NUMBER = os.getenv("RECIPIENT_WHATSAPP_NUMBER")
IMAGE_HOST_URL = os.getenv("IMAGE_HOST_URL", "https://your_public_hosting_url.com/")

# Cooldown
last_alert_time = {}
ALERT_COOLDOWN = 30  # seconds

def send_email(subject, body, attachment_path=None):
    if not all([EMAIL_SENDER, EMAIL_RECEIVER, EMAIL_PASSWORD]):
        print("❌ Email credentials are not configured properly.")
        return

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
    if not all([ACCOUNT_SID, AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER, RECIPIENT_WHATSAPP_NUMBER]):
        print("❌ Twilio credentials are not configured properly.")
        return

    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    image_url = IMAGE_HOST_URL + os.path.basename(image_path)
    try:
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=RECIPIENT_WHATSAPP_NUMBER,
            media_url=[image_url]
        )
        print(f"✅ WhatsApp message sent: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")

def save_intruder_image(frame):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(INTRUDER_IMAGES_DIR, f"intruder_{timestamp}.jpg")
    cv2.imwrite(image_path, frame)
    return image_path

def handle_intruder(face_id, frame):
    global last_alert_time
    now = time.time()

    if face_id in last_alert_time and now - last_alert_time[face_id] < ALERT_COOLDOWN:
        print(f"⚠️ Cooldown active for face {face_id}. Skipping alert.")
        return

    last_alert_time[face_id] = now
    print(f"🚨 Intruder detected! Face ID: {face_id}")

    intruder_image = save_intruder_image(frame)
    send_email(
        subject=f"Intruder Alert: Face ID {face_id}",
        body="An unauthorized person has been detected.",
        attachment_path=intruder_image
    )
    send_whatsapp_message(
        image_path=intruder_image,
        message_body="⚠️ Alert! An intruder has been detected."
    )

def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for face_id, (x, y, w, h) in enumerate(faces):
        face = gray[y:y+h, x:x+w]
        try:
            label, confidence = recognizer.predict(face)
        except:
            continue

        if confidence < 80:
            user_name = label_dict.get(str(label), "Unknown")
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{user_name} ({confidence:.2f})", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        else:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
            cv2.putText(frame, "Intruder", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            handle_intruder(face_id, frame)
    return frame

def detect_intruder():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam not available.")
        return

    print("📹 Intruder detection running. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        processed_frame = process_frame(frame)
        cv2.imshow("Intruder Detection", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def recognize_face():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Cannot access webcam.")
        return "fail"

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
                if confidence < 50:
                    user_name = label_dict.get(str(label), "Unknown")
                    print(f"✅ Recognized as {user_name} (Confidence: {confidence:.2f})")
                    recognized = True
                    break
            except:
                continue
        if recognized:
            break
        attempts += 1

    cam.release()
    cv2.destroyAllWindows()
    return "success" if recognized else "fail"

if __name__ == "__main__":
    print("✅ Module loaded.")
