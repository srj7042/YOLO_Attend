import os
import json
import cv2
import numpy as np
from pathlib import Path
from ai.detector import (
    detect_and_encode_faces,
    train_student_biometrics,
    validate_image_quality,
    cosine_similarity,
    normalize_embedding
)

class StudentBiometricIndex:
    """
    In-memory vectorized biometric index for fast batch matrix matching.
    Pre-normalizes and packs all student embeddings into a contiguous 2D float32 matrix.
    Computes cross-student similarities via BLAS matrix dot product.
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

    def match_all_pairs(self, detected_encodings, threshold=0.58, img_idx=0):
        """
        Compute similarity scores for ALL detected faces across ALL enrolled students.
        Returns:
            candidates: list of all (face_id, student_id, score) pairs above threshold
            per_face_stats: dict mapping face_id -> {'best_student_id', 'best_score', 'student_scores'}
        """
        if self.is_empty or not detected_encodings:
            return [], {}

        faces_mat = np.array(detected_encodings, dtype=np.float32)
        if faces_mat.ndim == 1:
            faces_mat = faces_mat.reshape(1, -1)

        norms = np.linalg.norm(faces_mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        faces_mat = faces_mat / norms

        # Single BLAS matrix multiplication: (N_faces, 128) @ (128, Total_Vectors) -> (N_faces, Total_Vectors)
        similarity_matrix = np.dot(faces_mat, self.matrix.T)

        candidates = []
        per_face_stats = {}

        for face_idx in range(len(faces_mat)):
            row_sims = similarity_matrix[face_idx]
            f_id = f"{img_idx}_{face_idx}"
            best_student_id = None
            best_score = -1.0
            student_scores = {}

            for s_id, (start, end) in self.student_slices.items():
                dots = row_sims[start:end]
                if len(dots) == 0:
                    continue
                max_s = float(np.max(dots))
                k = min(3, len(dots))
                top3_avg = float(np.mean(np.partition(dots, -k)[-k:]))
                comb_score = 0.65 * top3_avg + 0.35 * max_s
                student_scores[s_id] = float(comb_score)

                if comb_score > best_score:
                    best_score = comb_score
                    best_student_id = s_id

                if comb_score >= threshold:
                    candidates.append({
                        'face_id': f_id,
                        'face_idx': face_idx,
                        'img_idx': img_idx,
                        'student_id': s_id,
                        'confidence': float(comb_score)
                    })

            per_face_stats[f_id] = {
                'best_student_id': best_student_id,
                'best_score': max(0.0, float(best_score)),
                'student_scores': student_scores
            }

        return candidates, per_face_stats


def annotate_attendance_image(image_path, face_detections, face_assignments, output_path=None):
    """
    Draw colored bounding boxes and student names / confidence scores on the attendance image:
    - GREEN: Recognized student with Name & Similarity %
    - AMBER / RED: Unknown face with Best Similarity %
    """
    if not os.path.exists(image_path):
        return None

    img = cv2.imread(image_path)
    if img is None:
        return None

    h, w = img.shape[:2]
    # Scale font and line thickness based on image resolution
    thickness = max(2, int(max(h, w) / 700))
    font_scale = max(0.45, max(h, w) / 2200)

    for f_idx, det in enumerate(face_detections):
        box = det.get('box', (0, 0, 0, 0))
        x, y, fw, fh = box
        assignment = face_assignments.get(f_idx)

        if assignment and assignment.get('status') == 'recognized':
            name = assignment.get('name', 'Student')
            conf_pct = assignment.get('confidence', 0.0) * 100
            label = f"{name} ({conf_pct:.1f}%)"
            box_color = (45, 180, 75)   # Green
            bg_color = (35, 140, 60)
        else:
            best_sim = (assignment.get('best_score', 0.0) if assignment else 0.0) * 100
            label = f"? Unknown ({best_sim:.1f}%)"
            box_color = (0, 140, 255)   # Amber
            bg_color = (0, 100, 200)

        # Draw bounding rectangle around face
        cv2.rectangle(img, (x, y), (x + fw, y + fh), box_color, thickness)

        # Draw label background header
        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        header_y1 = max(0, y - th - 10)
        header_y2 = y
        cv2.rectangle(img, (x, header_y1), (min(w, x + tw + 10), header_y2), bg_color, -1)
        cv2.putText(img, label, (x + 5, header_y2 - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), max(1, thickness - 1))

    if not output_path:
        dir_name = os.path.dirname(image_path)
        base_name = os.path.basename(image_path)
        output_path = os.path.join(dir_name, f"annotated_{base_name}")

    cv2.imwrite(output_path, img)
    return output_path


def process_attendance(image_paths, students, threshold=0.60, deep_scan=False, progress_callback=None):
    """
    Process classroom photos and match detected faces against student biometrics.
    Uses YuNet deep face localization + StudentBiometricIndex BLAS matching + Global 1-to-1 Assignment.
    Detects and processes ALL visible faces, marks recognized students, and explicitly tracks Unknowns.
    """
    effective_threshold = 0.55 if deep_scan else threshold

    # Default attendance results: all absent initially
    results = {
        s.id: {
            'status': 'absent',
            'confidence': 0.0,
            'name': s.name,
            'student_id': s.student_id
        } for s in students
    }

    students_with_faces = [s for s in students if s.get_encoding() and len(s.get_encoding()) > 0]
    students_map = {s.id: s for s in students}

    summary = {
        'total_faces_detected': 0,
        'recognized_count': 0,
        'unknown_count': 0,
        'recognized_students': [],
        'unknown_faces': [],
        'annotated_images': []
    }

    if not students_with_faces:
        if progress_callback:
            progress_callback(100, "No students enrolled with biometrics.")
        return {'records': results, 'summary': summary}

    if progress_callback:
        progress_callback(15, f"Building biometric index for {len(students_with_faces)} enrolled students...")

    index = StudentBiometricIndex(students_with_faces)
    all_candidates = []
    all_per_face_stats = {}
    images_faces_meta = {}

    total_images = len(image_paths)
    for img_idx, img_path in enumerate(image_paths):
        if progress_callback:
            pct = 20 + int((img_idx / max(1, total_images)) * 50)
            progress_callback(pct, f"Detecting all faces in classroom photo {img_idx + 1}/{total_images}...")

        # Detect all faces and get bounding box metadata
        faces_meta = detect_and_encode_faces(img_path, deep_scan=deep_scan, return_metadata=True)
        images_faces_meta[img_idx] = faces_meta
        summary['total_faces_detected'] += len(faces_meta)

        if faces_meta:
            encodings = [f['embedding'] for f in faces_meta]
            candidates, per_face_stats = index.match_all_pairs(encodings, threshold=effective_threshold, img_idx=img_idx)
            all_candidates.extend(candidates)
            all_per_face_stats.update(per_face_stats)

    if progress_callback:
        progress_callback(75, "Resolving optimal 1-to-1 global student face assignments...")

    # Global Optimal 1-to-1 Greedy Assignment (sorted by highest confidence score)
    all_candidates.sort(key=lambda x: x['confidence'], reverse=True)
    assigned_faces = {}    # face_id -> {'student_id', 'confidence'}
    assigned_students = {} # student_id -> {'face_id', 'confidence'}

    for cand in all_candidates:
        s_id = cand['student_id']
        f_id = cand['face_id']
        conf = cand['confidence']

        if s_id not in assigned_students and f_id not in assigned_faces:
            assigned_students[s_id] = {'face_id': f_id, 'confidence': conf}
            assigned_faces[f_id] = {'student_id': s_id, 'confidence': conf}

            # Update student attendance record
            results[s_id]['confidence'] = round(conf, 3)
            results[s_id]['status'] = 'present'

            student_obj = students_map.get(s_id)
            student_name = student_obj.name if student_obj else f"Student #{s_id}"
            reg_id = student_obj.student_id if student_obj else ""
            summary['recognized_students'].append({
                'id': s_id,
                'name': student_name,
                'student_id': reg_id,
                'confidence': round(conf * 100, 1),
                'face_id': f_id
            })

    summary['recognized_count'] = len(assigned_students)

    # Process all unassigned detected faces as Unknown
    for img_idx, faces_meta in images_faces_meta.items():
        for face_idx in range(len(faces_meta)):
            f_id = f"{img_idx}_{face_idx}"
            if f_id not in assigned_faces:
                stats = all_per_face_stats.get(f_id, {})
                best_score = stats.get('best_score', 0.0)
                best_sid = stats.get('best_student_id')
                best_s_obj = students_map.get(best_sid)
                best_name = best_s_obj.name if best_s_obj else None
                summary['unknown_faces'].append({
                    'face_id': f_id,
                    'face_index': face_idx + 1,
                    'img_idx': img_idx,
                    'face_idx': face_idx,
                    'best_match_name': best_name,
                    'best_similarity': round(best_score * 100, 1),
                    'box': faces_meta[face_idx].get('box')
                })

    summary['unknown_count'] = len(summary['unknown_faces'])
    # Convenience aliases for templates and API responses
    summary['total_faces'] = summary['total_faces_detected']
    summary['recognized'] = summary['recognized_students']
    summary['unknown'] = summary['unknown_faces']

    # Annotate and save images with visual bounding boxes
    if progress_callback:
        progress_callback(88, "Drawing visual bounding boxes on attendance photo...")

    for img_idx, img_path in enumerate(image_paths):
        faces_meta = images_faces_meta.get(img_idx, [])
        if not faces_meta:
            continue

        face_assignments = {}
        for face_idx in range(len(faces_meta)):
            f_id = f"{img_idx}_{face_idx}"
            if f_id in assigned_faces:
                s_id = assigned_faces[f_id]['student_id']
                s_obj = students_map.get(s_id)
                face_assignments[face_idx] = {
                    'status': 'recognized',
                    'student_id': s_id,
                    'name': s_obj.name if s_obj else f"Student #{s_id}",
                    'confidence': assigned_faces[f_id]['confidence']
                }
            else:
                stats = all_per_face_stats.get(f_id, {})
                face_assignments[face_idx] = {
                    'status': 'unknown',
                    'best_score': stats.get('best_score', 0.0)
                }

        session_dir = os.path.dirname(img_path)
        base_name = os.path.basename(img_path)
        annotated_path = os.path.join(session_dir, f"annotated_{base_name}")
        saved_annotated = annotate_attendance_image(img_path, faces_meta, face_assignments, output_path=annotated_path)
        if saved_annotated:
            summary['annotated_images'].append(os.path.basename(saved_annotated))

    if progress_callback:
        progress_callback(100, f"Complete: {summary['recognized_count']} recognized, {summary['unknown_count']} unknown.")

    return {'records': results, 'summary': summary}


def compute_model_metrics(eval_data):
    """
    Compute rigorous biometric performance evaluation metrics:
    - Accuracy, Precision, Recall, F1-Score
    - True Positives (TP), False Positives (FP), False Negatives (FN), True Negatives (TN)
    - False Acceptance Rate (FAR) and False Rejection Rate (FRR)
    eval_data format: list of {'predicted_id': int or None, 'true_id': int or None, 'confidence': float}
    """
    if not eval_data:
        return {
            'total_samples': 0,
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'far': 0.0,
            'frr': 0.0,
            'tp': 0,
            'fp': 0,
            'fn': 0,
            'tn': 0,
            'has_eval_data': False
        }

    tp = 0 # Correctly recognized enrolled student
    fp = 0 # Recognized as student A when actually student B or Unknown
    fn = 0 # Enrolled student missed or marked as Unknown
    tn = 0 # Unknown person correctly flagged as Unknown

    for sample in eval_data:
        pred = sample.get('predicted_id')
        true = sample.get('true_id')

        if true is not None and pred is not None:
            if true == pred:
                tp += 1
            else:
                fp += 1
        elif true is not None and pred is None:
            fn += 1
        elif true is None and pred is not None:
            fp += 1
        elif true is None and pred is None:
            tn += 1

    total = len(eval_data)
    accuracy = round(((tp + tn) / max(1, total)) * 100, 2)
    precision = round((tp / max(1, tp + fp)) * 100, 2)
    recall = round((tp / max(1, tp + fn)) * 100, 2)
    f1 = round((2 * precision * recall / max(0.01, precision + recall)), 2)

    # FAR: False Acceptances / Total Impostor Trials
    total_impostors = sum(1 for s in eval_data if s.get('true_id') is None)
    far = round((fp / max(1, total_impostors)) * 100, 2) if total_impostors > 0 else 0.0

    # FRR: False Rejections / Total Genuine Trials
    total_genuine = sum(1 for s in eval_data if s.get('true_id') is not None)
    frr = round((fn / max(1, total_genuine)) * 100, 2) if total_genuine > 0 else 0.0

    return {
        'total_samples': total,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'far': far,
        'frr': frr,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'tn': tn,
        'has_eval_data': True
    }


def generate_face_embeddings(image_paths):
    """
    Generate optimized face embeddings from training photos using:
    - Quality & blur validation
    - Realistic data augmentation
    - L2 normalization & cosine deduplication
    """
    res = train_student_biometrics(image_paths)
    return res.get('embeddings', [])
