import os
import json
import numpy as np
from pathlib import Path
from ai.detector import (
    detect_and_encode_faces,
    match_face_to_students,
    train_student_biometrics,
    validate_image_quality,
    cosine_similarity
)

def process_attendance(image_paths, students, threshold=0.6, deep_scan=False):
    """
    Process classroom photos and match detected faces against student biometrics.
    Uses strict threshold matching and vectorized matrix cosine comparison.
    """
    effective_threshold = 0.65 if deep_scan else threshold
    
    results = {s.id: {'status': 'absent', 'confidence': 0.0, 'name': s.name,
                       'student_id': s.student_id} for s in students}

    students_with_faces = [s for s in students if s.get_encoding() and len(s.get_encoding()) > 0]
    if not students_with_faces:
        return results

    for img_path in image_paths:
        encodings = detect_and_encode_faces(img_path, deep_scan=deep_scan)

        for enc in encodings:
            student, conf = match_face_to_students(enc, students_with_faces, effective_threshold)
            if student:
                # Keep highest confidence match
                if conf > results[student.id]['confidence']:
                    results[student.id]['confidence'] = round(conf, 3)
                    results[student.id]['status'] = 'present'

    return results


def generate_face_embeddings(image_paths):
    """
    Generate optimized face embeddings from training photos (4-5 images) using:
    - Quality & blur validation
    - Realistic data augmentation (mirroring, CLAHE, illumination shifts)
    - L2 normalization & cosine deduplication
    """
    res = train_student_biometrics(image_paths)
    return res.get('embeddings', [])


