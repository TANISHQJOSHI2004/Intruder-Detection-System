import cv2
import os
import numpy as np
from datetime import datetime  # ✅ Import for timestamp

# Consistent base directory with remote_logs_server.py
BASE_DIR = r"C:\Users\TANISHQ JOSHI\Desktop\IDS\datasets"

def capture_faces(user_name):
    if not user_name:
        print("Error: Username is required.")
        return

    # User-specific folder
    user_folder = os.path.join(BASE_DIR, "intruder_images", user_name)
    os.makedirs(user_folder, exist_ok=True)

    # Initialize webcam and face detector
    camera = cv2.VideoCapture(0)
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

    if not os.path.exists(face_cascade_path):
        print(f"Error: Haarcascade file not found at {face_cascade_path}")
        return

    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    if not camera.isOpened():
        print("Error: Unable to access the camera.")
        return

    print(f"Capturing face images for {user_name}. Press 'q' to quit.")
    count = 0
    target_images = 100  # Adjust as needed

    while count < target_images:
        ret, frame = camera.read()
        if not ret:
            print("Error: Unable to capture frame from the camera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face, (150, 150))  # Standard size

            # Save original face with timestamp and username
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            file_name = f"{user_name}_{timestamp}.jpg"
            full_path = os.path.join(user_folder, file_name)
            cv2.imwrite(full_path, face_resized)
            print(f"Captured face {count}: {full_path}")
            count += 1

            # Data augmentation
            augmented_faces = augment_image(face_resized)
            for aug_face in augmented_faces:
                aug_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                aug_file_name = f"{user_name}_{aug_timestamp}.jpg"
                aug_full_path = os.path.join(user_folder, aug_file_name)
                cv2.imwrite(aug_full_path, aug_face)
                print(f"Captured augmented face {count}: {aug_full_path}")
                count += 1

            if count >= target_images:
                break

            # Draw rectangle on the frame
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

        cv2.imshow("Face Capture", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()
    print(f"Face capture complete. Total images: {count}")
    print(f"Images saved in: {user_folder}")

def augment_image(face_img):
    """Augments the given face image with small rotations and a horizontal flip."""
    augmented = []
    rows, cols = face_img.shape

    # Slight rotations
    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        rotated = cv2.warpAffine(face_img, M, (cols, rows), borderMode=cv2.BORDER_REFLECT)
        augmented.append(rotated)

    # Horizontal flip
    flipped = cv2.flip(face_img, 1)
    augmented.append(flipped)

    return augmented
