import os
import sys
import time
import cv2
from ai.detector import _get_yolo_model, detect_and_encode_faces

def test_image_accuracy(image_path, output_dir="test_output"):
    """
    Test YOLO detection and face encoding accuracy on a test image.
    Saves visual bounding boxes and extracted face crops.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    crops_dir = os.path.join(output_dir, "face_crops")
    os.makedirs(crops_dir, exist_ok=True)

    print(f"\n--- Testing Accuracy on: {image_path} ---")
    start_time = time.time()

    # 1. Load image & YOLO model
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not open image {image_path}")
        return

    model = _get_yolo_model()
    
    # 2. Run detection with upgraded settings
    h, w = img.shape[:2]
    scale = 3000 / w if w > 3000 else 1.0
    img_detect = cv2.resize(img, (0, 0), fx=scale, fy=scale) if scale != 1.0 else img
    
    results = model(img_detect, conf=0.20, iou=0.45, imgsz=1280, classes=[0], verbose=False)
    boxes = results[0].boxes

    detect_time = time.time() - start_time
    print(f"[YOLO Detection] Found {len(boxes)} faces/people in {detect_time:.2f} seconds.")

    # 3. Draw bounding boxes and extract crops
    annotated_img = img.copy()
    orig_h, orig_w = img.shape[:2]
    detect_h, detect_w = img_detect.shape[:2]

    for i, box in enumerate(boxes):
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        # Rescale
        x1 = int(x1 * orig_w / detect_w)
        x2 = int(x2 * orig_w / detect_w)
        y1 = int(y1 * orig_h / detect_h)
        y2 = int(y2 * orig_h / detect_h)

        # Head region crop
        box_h = y2 - y1
        head_y2 = y1 + int(box_h * 0.45) if box_h > 40 else y2

        pad = 10
        crop = img[max(0, y1 - pad):min(orig_h, head_y2 + pad),
                   max(0, x1 - pad):min(orig_w, x2 + pad)]

        # Save crop
        if crop.size > 0:
            crop_file = os.path.join(crops_dir, f"face_{i+1}_conf_{conf:.2f}.jpg")
            cv2.imwrite(crop_file, crop)

        # Draw box on annotated image
        cv2.rectangle(annotated_img, (x1, y1), (x2, head_y2), (0, 255, 0), 2)
        cv2.putText(annotated_img, f"Face #{i+1} ({conf:.2f})", (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Save annotated full image
    annotated_path = os.path.join(output_dir, "annotated_result.jpg")
    cv2.imwrite(annotated_path, annotated_img)

    # 4. Test face encodings
    encodings = detect_and_encode_faces(image_path)
    total_time = time.time() - start_time

    print(f"[Face Encoding] Successfully generated {len(encodings)} face embeddings.")
    print(f"[Total Time] {total_time:.2f} seconds.")
    print(f"\nResults saved to folder: '{os.path.abspath(output_dir)}/'")
    print(f"  - Annotated full image: {annotated_path}")
    print(f"  - Individual face crops: {crops_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] != "path/to/classroom_photo.jpg":
        test_image_accuracy(sys.argv[1])
    else:
        # Search for any sample image in the current directory or uploads folder
        sample_images = [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not sample_images and os.path.exists('uploads'):
            sample_images = [os.path.join('uploads', f) for f in os.listdir('uploads') if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if sample_images:
            print(f"No image path specified. Auto-testing using found sample image: '{sample_images[0]}'")
            test_image_accuracy(sample_images[0])
        else:
            print("\n[!] Please specify the actual path to your photo file.")
            print("Example usage:")
            print("  python test_accuracy.py C:\\Users\\Admin\\Pictures\\classroom.jpg")
            print("  python test_accuracy.py my_classroom.jpg  (if saved inside SmartAttend-main folder)")
