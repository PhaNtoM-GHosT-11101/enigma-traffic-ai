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

def get_all_violations(db_path="traffic.db"):
    """Return all violation records as a list of dicts, newest first."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, timestamp, plate_number, violation_types, confidence_scores,
               vehicle_class, camera_location_tag, pdf_path
        FROM violations
        ORDER BY timestamp DESC
        LIMIT 100
    ''')
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'plate_number': row['plate_number'],
            'violation_types': json.loads(row['violation_types']),
            'confidence_scores': json.loads(row['confidence_scores']),
            'vehicle_class': row['vehicle_class'],
            'camera_location_tag': row['camera_location_tag'],
            'pdf_path': row['pdf_path'],
        })
    return result
