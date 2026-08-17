# Security, Performance & Testing

## Security Architecture & Controls

1. **Authentication & Session Management**:
   - Password Hashing: Password storage via `werkzeug.security.generate_password_hash` (`pbkdf2:sha256`). Plaintext passwords never stored.
   - Authentication Guard: Flask-Login manages HTTP session cookies. Routes protected with `@login_required`.
   - Role-Based Access Control (RBAC): Custom Python decorators `@admin_required` and `@teacher_required` strictly check `current_user.role` on every endpoint request.
   - Account Activation Guard: Unapproved teacher accounts (`is_active_account=False`) are blocked from administrative and attendance operations.
2. **File Upload Security**:
   - Allowed Extensions: Sanitized via `ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}`.
   - Filename Sanitization: `secure_filename()` applied to all incoming upload filenames before disk writing to mitigate path traversal vulnerabilities.
   - Payload Limit: Enforced via Flask `MAX_CONTENT_LENGTH = 16 * 1024 * 1024` (16 MB maximum request payload).

## Performance Optimization

1. **AI Model Caching (Lazy Loading)**:
   - YOLOv8 Medium model cached at module-level `_yolo_model` in [ai/detector.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/ai/detector.py#L7) to prevent heavy 50MB+ weights reload on every HTTP request.
2. **Thread Safety & Execution Constraints**:
   - DeepFace representations run sequentially to prevent TensorFlow thread-race condition crashes under concurrent Flask request threads.
3. **Resolution-Aware Scaling**:
   - Images with width $> 3000\text{px}$ are scaled down proportionally (`scale = 3000 / w`) before detection to optimize GPU/CPU memory consumption while retaining small-face detection accuracy at `imgsz=1280`.
4. **Targeted Head Region Cropping**:
   - DeepFace processing is restricted to upper 45% crop of person bounding boxes (`y1 + int(box_h * 0.45)`), ignoring torso/clothing clutter to accelerate embedding computation.

## Testing & Accuracy Verification

- Script: [test_accuracy.py](file:///Users/surajjaiswal/SmartAttend-main_sujal/test_accuracy.py)
- Execution: `python test_accuracy.py <path_to_image>`
- Functionality:
  - Loads sample classroom image.
  - Measures YOLO detection latency and box count.
  - Draws green bounding boxes over detected face regions and outputs `annotated_result.jpg`.
  - Saves extracted individual face crops into `test_output/face_crops/`.
  - Runs DeepFace representation and measures total pipeline execution time.
