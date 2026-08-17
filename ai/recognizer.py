import os
import json
import tempfile
import numpy as np
from pathlib import Path
from ai.detector import detect_and_encode_faces, match_face_to_students

def process_attendance(image_paths, students, threshold=0.6, deep_scan=False):
    """
    Process classroom photos and match faces to students.
    Strictly ignores any matches with confidence below the threshold.
    """
    # If deep scan is on, we use an even stricter threshold for final confirmation
    effective_threshold = 0.65 if deep_scan else threshold
    
    results = {s.id: {'status': 'absent', 'confidence': 0.0, 'name': s.name,
                       'student_id': s.student_id} for s in students}

    students_with_faces = [s for s in students if s.get_encoding()]
    if not students_with_faces:
        return results

    matched_ids = set()

    for img_path in image_paths:
        encodings = detect_and_encode_faces(img_path, deep_scan=deep_scan)

        for enc in encodings:
            student, conf = match_face_to_students(enc, students_with_faces, effective_threshold)
            if student:
                # Always keep the highest confidence match
                if conf > results[student.id]['confidence']:
                    results[student.id]['confidence'] = round(conf, 3)
                    results[student.id]['status'] = 'present'

    return results


def generate_face_embeddings(image_paths):
    """
    Generate face embeddings from multiple training images of a student.
    Returns list of embeddings (each is a 128-dim list).
    """
    embeddings = []
    for img_path in image_paths:
        encs = detect_and_encode_faces(img_path)
        # Take up to 2 faces per image to avoid too many false positives
        embeddings.extend(encs[:2])
    return embeddings

