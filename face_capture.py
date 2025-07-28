import cv2
import os
import numpy as np
from datetime import datetime

# Dataset base path (authorized users)
BASE_DIR = r"C:\Users\TANISHQ JOSHI\Desktop\IDS\datasets"

def sanitize_name(name):
    # Remove leading/trailing spaces and replace spaces with underscores (but keep original casing)
    return name.strip().replace(" ", "_")

def capture_faces(user_name):
    if not user_name:
        print("Error: Username is required.")
        return

    # Create user-specific folder in datasets (case-sensitive)
    folder_name = sanitize_name(user_name)
    user_folder = os.path.join(BASE_DIR, folder_name)
    os.makedirs(user_folder, exist_ok=True)

    # Initialize camera
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    if not os.path.exists(face_cascade_path):
        print(f"Error: Haarcascade not found at {face_cascade_path}")
        return

    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    if not camera.isOpened():
        print("Error: Unable to access the camera.")
        return

    print(f"[INFO] Capturing face images for '{user_name}'. Press 'q' to quit.")
    count = 0
    target_images = 100

    while count < target_images:
        ret, frame = camera.read()
        if not ret:
            print("[ERROR] Unable to read from camera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face, (150, 150))

            # Save the face image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{folder_name}_{timestamp}.jpg"
            full_path = os.path.join(user_folder, filename)
            cv2.imwrite(full_path, face_resized)
            print(f"[SAVED] {full_path}")
            count += 1

            # Data augmentation
            for aug_face in augment_image(face_resized):
                aug_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                aug_filename = f"{folder_name}_{aug_timestamp}.jpg"
                aug_path = os.path.join(user_folder, aug_filename)
                cv2.imwrite(aug_path, aug_face)
                print(f"[AUGMENTED] {aug_path}")
                count += 1

            if count >= target_images:
                break

            # Show face box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        cv2.imshow("Face Capture - Press 'q' to quit", frame)

        if cv2.waitKey(1000) & 0xFF == ord('q'):
            print("[INFO] Exit key pressed.")
            break

    camera.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Face capture complete. Total images: {count}")
    print(f"📁 Saved at: {user_folder}")

def augment_image(face_img):
    """Augments the face with slight rotations and a flip."""
    augmented = []
    rows, cols = face_img.shape

    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        rotated = cv2.warpAffine(face_img, M, (cols, rows), borderMode=cv2.BORDER_REFLECT)
        augmented.append(rotated)

    flipped = cv2.flip(face_img, 1)
    augmented.append(flipped)

    return augmented

# Run directly (for testing)
if __name__ == "__main__":
    name_input = input("Enter authorized user's name: ")
    capture_faces(name_input)
