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

class StudentBiometricIndex:
    """
    In-memory vectorized biometric index for fast batch matrix matching.
    Pre-normalizes and packs all student embeddings into a contiguous 2D float32 matrix.
    Computes all cross-student similarities via a single BLAS matrix dot product.
    """
    def __init__(self, students):
        self.students_dict = {}
        all_vecs = []
        student_slices = {} # student_id -> (start_idx, end_idx)

        current_idx = 0
        for s in students:
            enc = s.get_encoding()
            if not enc or len(enc) == 0:
                continue

            self.students_dict[s.id] = s
            mat = np.array(enc, dtype=np.float32)
            if mat.ndim == 1:
                mat = mat.reshape(1, -1)

            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            mat = mat / norms

            count = len(mat)
            all_vecs.append(mat)
            student_slices[s.id] = (current_idx, current_idx + count)
            current_idx += count

        if all_vecs:
            self.matrix = np.vstack(all_vecs) # Shape: (Total_Vectors, 128)
            self.student_slices = student_slices
        else:
            self.matrix = np.empty((0, 128), dtype=np.float32)
            self.student_slices = {}

    @property
    def is_empty(self):
        return self.matrix.shape[0] == 0

    def match_faces_batch(self, detected_encodings, threshold=0.55, img_idx=0):
        """
        Match detected face encodings against the indexed student matrix using a single matrix dot product.
        Returns list of candidate matches: [{'student_id', 'confidence', 'face_id'}]
        """
        if self.is_empty or not detected_encodings:
            return []

        faces_mat = np.array(detected_encodings, dtype=np.float32)
        if faces_mat.ndim == 1:
            faces_mat = faces_mat.reshape(1, -1)

        norms = np.linalg.norm(faces_mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        faces_mat = faces_mat / norms

        # Single BLAS matrix multiplication: (N_faces, 128) @ (128, Total_Vectors) -> (N_faces, Total_Vectors)
        similarity_matrix = np.dot(faces_mat, self.matrix.T)

        candidates = []
        for face_idx in range(len(faces_mat)):
            row_sims = similarity_matrix[face_idx]
            best_student_id = None
            best_score = 0.0

            for s_id, (start, end) in self.student_slices.items():
                dots = row_sims[start:end]
                if len(dots) == 0:
                    continue
                max_s = float(np.max(dots))
                k = min(3, len(dots))
                top3_avg = float(np.mean(np.partition(dots, -k)[-k:]))
                comb_score = 0.70 * top3_avg + 0.30 * max_s

                if comb_score > best_score:
                    best_score = comb_score
                    best_student_id = s_id

            if best_student_id is not None and best_score >= threshold:
                candidates.append({
                    'student_id': best_student_id,
                    'confidence': float(best_score),
                    'face_id': f"{img_idx}_{face_idx}"
                })

        return candidates


def process_attendance(image_paths, students, threshold=0.55, deep_scan=False, progress_callback=None):
    """
    Process classroom photos and match detected faces against student biometrics.
    Uses StudentBiometricIndex for high-speed vectorized BLAS similarity computations.
    """
    effective_threshold = 0.58 if deep_scan else threshold

    results = {s.id: {'status': 'absent', 'confidence': 0.0, 'name': s.name,
                       'student_id': s.student_id} for s in students}

    students_with_faces = [s for s in students if s.get_encoding() and len(s.get_encoding()) > 0]
    if not students_with_faces:
        if progress_callback:
            progress_callback(100, "No students enrolled with biometrics.")
        return results

    if progress_callback:
        progress_callback(15, f"Building vectorized index for {len(students_with_faces)} students...")

    index = StudentBiometricIndex(students_with_faces)
    candidates = []

    total_images = len(image_paths)
    for img_idx, img_path in enumerate(image_paths):
        if progress_callback:
            pct = 20 + int((img_idx / max(1, total_images)) * 60)
            progress_callback(pct, f"Detecting and encoding faces in photo {img_idx + 1}/{total_images}...")

        encodings = detect_and_encode_faces(img_path, deep_scan=deep_scan)
        if encodings:
            batch_candidates = index.match_faces_batch(encodings, threshold=effective_threshold, img_idx=img_idx)
            candidates.extend(batch_candidates)

    if progress_callback:
        progress_callback(85, "Resolving optimal 1-to-1 student face assignments...")

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

    if progress_callback:
        progress_callback(100, f"Attendance complete: {len(assigned_students)} students marked present.")

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


