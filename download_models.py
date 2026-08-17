import os

print("--- Starting AI Model Pre-Download ---")

try:
    from ultralytics import YOLO
    print("1. Downloading YOLOv8 Medium model...")
    model = YOLO('yolov8m.pt')
    print("   YOLOv8 Medium ready.")
except Exception as e:
    print(f"   Error downloading YOLO: {e}")

try:
    from deepface import DeepFace
    print("2. Downloading FaceNet model for DeepFace...")
    # This triggers the download of Facenet weights (~90MB)
    DeepFace.build_model('Facenet')
    print("   DeepFace models ready.")
except Exception as e:
    print(f"   Error downloading DeepFace models: {e}")

print("--- All AI models and weights are now cached locally ---")
