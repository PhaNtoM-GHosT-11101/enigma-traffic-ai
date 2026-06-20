from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pipeline import process_pipeline
from database import init_db, get_all_violations
import uvicorn
import os, json, shutil, uuid

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db('traffic.db')
    yield

app = FastAPI(title="Enigma Traffic Violation API", lifespan=lifespan)

# ─── CORS — allow GitHub Pages and local dev ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Serve frontend assets (images, etc.) ─────────────────────────────────────
_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/frontend", StaticFiles(directory=_frontend_dir), name="frontend")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(current_dir, "..", "frontend", "index.html")
    if not os.path.exists(frontend_path):
        return HTMLResponse(
            status_code=500,
            content="<h1>500 Internal Server Error</h1><p>Frontend index.html is missing.</p>"
        )
    with open(frontend_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health():
    """Quick liveness check — frontend uses this to auto-switch to Live Mode."""
    return {"status": "ok", "model": "YOLOv8n + EasyOCR", "mode": "live"}


@app.get("/violations")
async def list_violations():
    """Return all violation records from SQLite for the Evidence Log."""
    try:
        rows = get_all_violations('traffic.db')
        return JSONResponse(content={"status": "ok", "violations": rows})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/process_image")
async def process_image(
    file: UploadFile = File(...),
    config: str = Form(...)
):
    try:
        conf_dict = json.loads(config)
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        raw_path = f"raw_input_{uuid.uuid4()}{ext}"
        with open(raw_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        result = process_pipeline(raw_path, conf_dict)
        return JSONResponse(content={"status": "success", **result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)


@app.get("/download/{pdf_filename}")
async def download_pdf(pdf_filename: str):
    if os.path.exists(pdf_filename):
        return FileResponse(pdf_filename, media_type="application/pdf", filename=pdf_filename)
    return JSONResponse(status_code=404, content={"message": "File not found"})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
