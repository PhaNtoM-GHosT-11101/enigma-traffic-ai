from fpdf import FPDF
import os

class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'Traffic Violation Report', 0, 1, 'C')

def generate_pdf(case_id, timestamp, plate_number, violation_types, confidences, camera_id, image_path, pdf_path):
    pdf = PDFReport()
    pdf.add_page()
    
    if os.path.exists(image_path):
        pdf.image(image_path, x=10, y=30, w=190)
    
    pdf.set_y(150)
    pdf.set_font("Helvetica", size=12)
    
    data = [
        ["Case ID", case_id],
        ["Timestamp", timestamp],
        ["Plate Number", plate_number],
        ["Violations", ", ".join(violation_types)],
        ["Confidences", ", ".join([f"{c:.2f}" for c in confidences])],
        ["Camera ID", camera_id]
    ]
    
    for row in data:
        pdf.cell(50, 10, str(row[0]), border=1)
        pdf.cell(140, 10, str(row[1]), border=1)
        pdf.ln()
        
    pdf.output(pdf_path)
