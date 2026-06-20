import sqlite3
import json

def init_db(db_path="traffic.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            original_image_path TEXT,
            evidence_image_path TEXT,
            pdf_path TEXT,
            plate_number TEXT,
            violation_types TEXT,
            confidence_scores TEXT,
            vehicle_class TEXT,
            camera_location_tag TEXT,
            reviewed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def insert_violation(db_path, data):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO violations 
        (id, timestamp, original_image_path, evidence_image_path, pdf_path, plate_number, violation_types, confidence_scores, vehicle_class, camera_location_tag, reviewed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        data['id'], data['timestamp'], data['original_image_path'], 
        data['evidence_image_path'], data['pdf_path'], data['plate_number'], 
        json.dumps(data['violation_types']), json.dumps(data['confidence_scores']),
        data['vehicle_class'], data['camera_location_tag']
    ))
    conn.commit()
    conn.close()
