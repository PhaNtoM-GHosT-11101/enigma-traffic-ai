import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
import re
import uuid
import datetime
import os
import base64
from database import insert_violation
from pdf_generator import generate_pdf

# ─── Load models globally ────────────────────────────────────────────────────
model_det = YOLO('yolov8n.pt')       # full-frame vehicle/person detection
model_pose = YOLO('yolov8n-pose.pt') # body keypoints for seatbelt check

# EasyOCR reader (CPU mode, English)
reader = easyocr.Reader(['en'], gpu=False)

# Haar cascades for face/helmet detection
face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(face_cascade_path)
profile_cascade_path = cv2.data.haarcascades + 'haarcascade_profileface.xml'
profile_cascade = cv2.CascadeClassifier(profile_cascade_path)

# ─── Helmet Detection via computer vision heuristic ──────────────────────────
def check_helmet_cv(head_crop):
    """
    Real helmet detection using two complementary signals:
    1. Face visibility: if a face is clearly detected, the rider is NOT wearing a
       full-face helmet (or is without one). Partial face = uncertain.
    2. Skin-tone ratio: large exposed skin area in upper region = no helmet.
    
    Returns (violation_detected, confidence)
    """
    if head_crop is None or head_crop.size == 0:
        return False, 0.0

    h, w = head_crop.shape[:2]
    gray = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)

    # Signal 1: face cascade detection
    faces_front = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
    faces_profile = profile_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
    face_detected = len(faces_front) > 0 or len(faces_profile) > 0

    # Signal 2: skin tone ratio using YCrCb colorspace
    ycrcb = cv2.cvtColor(head_crop, cv2.COLOR_BGR2YCrCb)
    skin_mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8),
                                   np.array([255, 173, 127], dtype=np.uint8))
    skin_ratio = np.sum(skin_mask > 0) / (h * w)

    # Signal 3: dark region at top (helmets are usually dark/opaque)
    top_quarter = head_crop[:h//3, :]
    top_gray = cv2.cvtColor(top_quarter, cv2.COLOR_BGR2GRAY)
    top_darkness = np.mean(top_gray)

    # Decision logic
    if face_detected and skin_ratio > 0.15:
        conf = min(0.95, 0.65 + skin_ratio)
        return True, round(conf, 2)
    elif skin_ratio > 0.30:
        return True, round(0.60 + skin_ratio * 0.5, 2)
    elif face_detected and top_darkness > 150:
        return True, 0.70
    else:
        return False, 0.0


def point_in_polygon(x, y, polygon):
    """Ray casting algorithm for point-in-polygon check."""
    num_vertices = len(polygon)
    x, y = float(x), float(y)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(num_vertices + 1):
        p2x, p2y = polygon[i % num_vertices]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def process_pipeline(image_path, config):
    # ─── Stage 1: Raw Input ──────────────────────────────────────────────────
    orig_img = cv2.imread(image_path)
    if orig_img is None:
        raise ValueError(f"Could not read image: {image_path}")

    # ─── Stage 2: Image Preprocessing ───────────────────────────────────────
    img = orig_img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_val = float(np.mean(gray))
    was_dark = mean_val < 80

    if was_dark:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        lab = cv2.merge((cl, a, b))
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    was_blurry = variance < 100

    if was_blurry:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        img = cv2.filter2D(img, -1, kernel)

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_640 = cv2.resize(img_rgb, (640, 640))

    preprocessing_info = {
        "mean_brightness": round(mean_val, 1),
        "blur_variance": round(variance, 1),
        "clahe_applied": was_dark,
        "sharpening_applied": was_blurry,
    }

    # ─── Stage 3: Full Frame Detection ──────────────────────────────────────
    results = model_det(img_640, verbose=False)
    vehicles = []
    persons = []

    VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck", 1: "bicycle"}
    PERSON_CLASS = 0

    h_orig, w_orig = orig_img.shape[:2]
    scale_x = w_orig / 640.0
    scale_y = h_orig / 640.0

    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < 0.4:
                continue
            cls = int(box.cls[0])
            b = box.xyxy[0].cpu().numpy()
            orig_bbox = [
                int(b[0] * scale_x), int(b[1] * scale_y),
                int(b[2] * scale_x), int(b[3] * scale_y)
            ]
            item = {
                'class': cls,
                'class_name': VEHICLE_CLASSES.get(cls, 'unknown'),
                'bbox': orig_bbox,
                'confidence': round(conf, 2)
            }
            if cls in VEHICLE_CLASSES:
                vehicles.append(item)
            elif cls == PERSON_CLASS:
                persons.append(item)

    # ─── Stage 4: Per-Vehicle Crop ───────────────────────────────────────────
    for v in vehicles:
        x1, y1, x2, y2 = v['bbox']
        h = y2 - y1
        v['head_crop'] = None
        v['driver_crop'] = None
        v['plate_crop'] = None

        if v['class'] == 3:  # motorcycle
            head_y2 = y1 + max(1, int(h * 0.3))
            v['head_crop'] = orig_img[y1:head_y2, x1:x2]

        if v['class'] == 2:  # car
            driver_y2 = y1 + max(1, int(h * 0.4))
            v['driver_crop'] = orig_img[y1:driver_y2, x1:x2]

        plate_y1 = y1 + max(0, int(h * 0.8))
        v['plate_crop'] = orig_img[plate_y1:y2, x1:x2]

    # ─── Stage 5: Face Detection & Body Keypoints ────────────────────────────
    for v in vehicles:
        face_count = 0
        seatbelt_present = True

        if v['head_crop'] is not None and v['head_crop'].size > 0:
            gray_crop = cv2.cvtColor(v['head_crop'], cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray_crop, 1.1, 4)
            face_count = len(faces)

        if v['driver_crop'] is not None and v['driver_crop'].size > 0:
            pose_res = model_pose(v['driver_crop'], verbose=False)
            seatbelt_present = False
            for r in pose_res:
                if r.keypoints is not None and len(r.keypoints.xy) > 0:
                    kpts = r.keypoints.xy[0].cpu().numpy()
                    if len(kpts) >= 12:
                        ls, rs = kpts[5], kpts[6]
                        lh, rh = kpts[11], kpts[12]
                        if ls[0] > 0 and rh[0] > 0:
                            seatbelt_present = True

        v['face_count'] = face_count
        v['seatbelt_present'] = seatbelt_present

    # ─── Stage 6: Violation Detection Engine ─────────────────────────────────
    violations = []
    stop_line_y    = config.get('stop_line_y', 9999)
    signal_roi     = config.get('signal_roi', [0, 0, 10, 10])
    lane_divider_x = config.get('lane_divider_x', -1)
    no_park_polys  = config.get('no_parking_polygons', [])

    sx1, sy1, sx2, sy2 = signal_roi
    sig_crop = orig_img[sy1:sy2, sx1:sx2]
    is_red_light = False
    if sig_crop.size > 0:
        hsv = cv2.cvtColor(sig_crop, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        if np.sum(mask1 | mask2) > 100:
            is_red_light = True

    for v in vehicles:
        x1, y1, x2, y2 = v['bbox']
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        bottom_y = y2
        v_class = v['class']

        detected_violations = []

        # 1. Helmet check (motorcycles only)
        if v_class == 3 and v['head_crop'] is not None:
            is_viol, conf = check_helmet_cv(v['head_crop'])
            if is_viol and conf >= 0.60:
                detected_violations.append({"type": "No Helmet", "confidence": conf, "color": (0, 0, 255)})

        # 2. Triple riding (motorcycles only)
        if v_class == 3 and v['face_count'] >= 3:
            detected_violations.append({"type": "Triple Riding", "confidence": 1.0, "color": (0, 140, 255)})

        # 3. Seatbelt (cars only)
        if v_class == 2 and not v['seatbelt_present']:
            detected_violations.append({"type": "No Seatbelt", "confidence": 0.85, "color": (0, 215, 255)})

        # 4. Stop line
        crossed_stop = bottom_y > stop_line_y
        if crossed_stop:
            detected_violations.append({"type": "Stop Line Crossed", "confidence": 1.0, "color": (0, 255, 0)})

        # 5. Red light
        if is_red_light and crossed_stop:
            detected_violations.append({"type": "Red Light Violation", "confidence": 1.0, "color": (128, 0, 128)})

        # 6. Wrong side
        if lane_divider_x > 0 and cx < lane_divider_x:
            detected_violations.append({"type": "Wrong Side Driving", "confidence": 0.80, "color": (255, 165, 0)})

        # 7. Illegal parking
        for poly in no_park_polys:
            if point_in_polygon(cx, cy, poly):
                detected_violations.append({"type": "Illegal Parking", "confidence": 1.0, "color": (255, 0, 255)})
                break

        if detected_violations:
            violations.append({
                'vehicle_bbox': v['bbox'],
                'vehicle_class': v['class_name'],
                'violations': detected_violations,
                'face_count': v['face_count'],
                'plate_crop': v['plate_crop'],
            })

    # ─── Stage 7: OCR (EasyOCR), Evidence Generation & Storage ──────────────
    annotated_img = orig_img.copy()
    case_id = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cv2.putText(annotated_img, f"ENIGMA AI  |  {timestamp}  |  Case: {case_id}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(annotated_img, f"ENIGMA AI  |  {timestamp}  |  Case: {case_id}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)

    all_results = []

    for viol in violations:
        plate_text = "UNKNOWN"
        if viol['plate_crop'] is not None and viol['plate_crop'].size > 0:
            try:
                ocr_results = reader.readtext(viol['plate_crop'])
                if ocr_results:
                    raw_text = " ".join([res[1] for res in ocr_results])
                    match = re.search(r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}', raw_text.replace(" ", "").upper())
                    plate_text = match.group(0) if match else raw_text.strip() or "UNKNOWN"
            except Exception:
                plate_text = "UNKNOWN"

        x1, y1, x2, y2 = viol['vehicle_bbox']
        viol_types = [v['type'] for v in viol['violations']]
        viol_confs = [v['confidence'] for v in viol['violations']]
        primary_color = viol['violations'][0]['color']

        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), primary_color, 3)

        label_y = y1 - 10
        for v_item in viol['violations']:
            label = f"{v_item['type']} ({v_item['confidence']*100:.0f}%)"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated_img, (x1, label_y - lh - 4), (x1 + lw + 4, label_y + 2), v_item['color'], -1)
            cv2.putText(annotated_img, label, (x1 + 2, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            label_y -= (lh + 8)

        cv2.putText(annotated_img, f"PLATE: {plate_text}", (x1, y2 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, primary_color, 2)

        evidence_path = f"evidence_{case_id}.jpg"
        cv2.imwrite(evidence_path, annotated_img)

        pdf_path = f"case_{case_id}.pdf"
        generate_pdf(case_id, timestamp, plate_text, viol_types, viol_confs,
                     config.get('camera_id', 'CAM-1'), evidence_path, pdf_path)

        db_data = {
            'id': case_id,
            'timestamp': timestamp,
            'original_image_path': image_path,
            'evidence_image_path': evidence_path,
            'pdf_path': pdf_path,
            'plate_number': plate_text,
            'violation_types': viol_types,
            'confidence_scores': viol_confs,
            'vehicle_class': viol['vehicle_class'],
            'camera_location_tag': config.get('camera_id', 'CAM-1'),
        }
        insert_violation('traffic.db', db_data)

        all_results.append({
            'case_id': case_id,
            'timestamp': timestamp,
            'vehicle_class': viol['vehicle_class'],
            'plate_number': plate_text,
            'violations': [{'type': v['type'], 'confidence': v['confidence']} for v in viol['violations']],
            'pdf_download_url': f"/download/{pdf_path}",
        })

    _, buffer = cv2.imencode('.jpg', annotated_img)
    b64 = base64.b64encode(buffer).decode('utf-8')

    return {
        'violations': all_results,
        'annotated_image': f"data:image/jpeg;base64,{b64}",
        'stats': {
            'vehicles_detected': len(vehicles),
            'persons_detected': len(persons),
            'violations_found': len(violations),
            'preprocessing': preprocessing_info,
        }
    }
