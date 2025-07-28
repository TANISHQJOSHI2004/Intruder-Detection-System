import cv2
import numpy as np
import os
import json

def augment_image(face_img):
    """Apply data augmentation (rotation and flip) on a single face image."""
    augmented = []
    rows, cols = face_img.shape

    # Slight rotations
    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)
        rotated = cv2.warpAffine(face_img, M, (cols, rows), borderMode=cv2.BORDER_REFLECT)
        augmented.append(rotated)

    # Horizontal flip
    flipped = cv2.flip(face_img, 1)
    augmented.append(flipped)

    return augmented

def train_model():
    # Set base directory to IDS folder on the desktop
    base_dir = os.path.join(os.path.expanduser("~/Desktop"), "IDS")
    dataset_path = os.path.join(base_dir, "datasets/")
    model_path = os.path.join(base_dir, "face_model.yml")
    label_mapping_path = os.path.join(base_dir, "label_mapping.json")

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset folder not found at {dataset_path}. Please create it and add user images.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    images, labels = [], []
    label_dict = {}

    # Get user directories with correct casing
    user_dirs = sorted([
        folder for folder in os.listdir(dataset_path)
        if os.path.isdir(os.path.join(dataset_path, folder))
    ])

    for label, user_name in enumerate(user_dirs):
        user_folder = os.path.join(dataset_path, user_name)

        for filename in os.listdir(user_folder):
            img_path = os.path.join(user_folder, filename)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            # Add original image
            images.append(img)
            labels.append(label)

            # Apply on-the-fly augmentation
            augmented_faces = augment_image(img)
            for aug_face in augmented_faces:
                images.append(aug_face)
                labels.append(label)

        label_dict[str(label)] = user_name  # Keep original name with case

    if not images:
        raise ValueError(f"No images found in dataset folder: {dataset_path}. Ensure each user folder contains images.")

    # Train and save the model
    recognizer.train(images, np.array(labels))
    recognizer.save(model_path)

    # Save label mapping
    with open(label_mapping_path, "w") as file:
        json.dump(label_dict, file, indent=4)

    print(f"✅ Model trained and saved to {model_path}")
    print(f"📁 Label mapping saved to {label_mapping_path}")
    print("👥 User mapping:")
    for k, v in label_dict.items():
        print(f"  Label {k}: {v}")

if __name__ == "__main__":
    train_model()
