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

def process_attendance(image_paths, students, threshold=0.84, deep_scan=False):
    """
    Process classroom photos and match detected faces against student biometrics.
    Strict verification (>=0.84 standard, >=0.88 deep scan) and 1-to-1 candidate sorting.
    """
    effective_threshold = 0.88 if deep_scan else threshold
    
    results = {s.id: {'status': 'absent', 'confidence': 0.0, 'name': s.name,
                       'student_id': s.student_id} for s in students}

    students_with_faces = [s for s in students if s.get_encoding() and len(s.get_encoding()) > 0]
    if not students_with_faces:
        return results

    candidates = []
    for img_idx, img_path in enumerate(image_paths):
        encodings = detect_and_encode_faces(img_path, deep_scan=deep_scan)

        for enc_idx, enc in enumerate(encodings):
            student, conf = match_face_to_students(enc, students_with_faces, effective_threshold)
            if student and conf >= effective_threshold:
                candidates.append({
                    'student_id': student.id,
                    'confidence': conf,
                    'face_id': f"{img_idx}_{enc_idx}"
                })

    # Sort candidates by highest confidence first (Global Optimal 1-to-1 Assignment)
    candidates.sort(key=lambda x: x['confidence'], reverse=True)
    assigned_faces = set()
    assigned_students = set()

    for cand in candidates:
        s_id = cand['student_id']
        f_id = cand['face_id']
        conf = cand['confidence']

        if s_id not in assigned_students and f_id not in assigned_faces:
            assigned_students.add(s_id)
            assigned_faces.add(f_id)
            results[s_id]['confidence'] = round(conf, 3)
            results[s_id]['status'] = 'present'

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


