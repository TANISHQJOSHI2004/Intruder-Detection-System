import cv2
import numpy as np
import os
import json

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

    # Ensure consistent label assignment
    user_dirs = sorted(os.listdir(dataset_path))

    for label, user_name in enumerate(user_dirs):
        user_folder = os.path.join(dataset_path, user_name)
        if not os.path.isdir(user_folder):
            continue  # skip non-folder files

        for filename in os.listdir(user_folder):
            img_path = os.path.join(user_folder, filename)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                images.append(img)
                labels.append(label)

        label_dict[str(label)] = user_name  # Save label as str for JSON

    if not images:
        raise ValueError(f"No images found in dataset folder: {dataset_path}. Ensure that each user folder contains image files.")

    # Train and save model
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
