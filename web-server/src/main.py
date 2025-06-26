from fastapi import FastAPI, Request, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
import httpx
import io

# App setup
app = FastAPI(title="Bioreactor Web Server", description="User interface for bioreactor experiments.")

# Static and template directories
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads_tmp"
UPLOADS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Hub API config (could be loaded from env)
HUB_API_URL = os.getenv("BIOREACTOR_HUB_API_URL", "http://localhost:8000")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload_script(request: Request, file: UploadFile = File(...)):
    # Validate file extension
    if not file.filename.endswith(".py"):
        return templates.TemplateResponse(
            "upload.html", {"request": request, "error": "Only .py files are allowed."}
        )
    # Save file to uploads_tmp
    file_location = UPLOADS_DIR / file.filename
    content = await file.read()
    with open(file_location, "wb") as f:
        f.write(content)
    # Submit to hub
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{HUB_API_URL}/api/experiments/start",
                json={"script_content": content.decode("utf-8")}
            )
        if resp.status_code == 200:
            data = resp.json()
            experiment_id = data.get("experiment_id")
            return templates.TemplateResponse(
                "upload.html", {
                    "request": request,
                    "success": f"Uploaded and submitted {file.filename} successfully.",
                    "experiment_id": experiment_id
                }
            )
        else:
            return templates.TemplateResponse(
                "upload.html", {"request": request, "error": f"Hub error: {resp.text}"}
            )
    except Exception as e:
        return templates.TemplateResponse(
            "upload.html", {"request": request, "error": f"Failed to submit to hub: {e}"}
        )

@app.get("/experiment/{experiment_id}", response_class=HTMLResponse)
async def experiment_status(request: Request, experiment_id: str):
    # Query hub for experiment status
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{HUB_API_URL}/api/experiments/{experiment_id}/status")
        if resp.status_code == 200:
            data = resp.json()
            return templates.TemplateResponse(
                "experiment_status.html", {"request": request, "experiment": data.get("experiment", {}), "experiment_id": experiment_id}
            )
        else:
            return templates.TemplateResponse(
                "experiment_status.html", {"request": request, "error": f"Hub error: {resp.text}", "experiment_id": experiment_id}
            )
    except Exception as e:
        return templates.TemplateResponse(
            "experiment_status.html", {"request": request, "error": f"Failed to contact hub: {e}", "experiment_id": experiment_id}
        )

@app.get("/experiment/{experiment_id}/download")
async def download_experiment_results(experiment_id: str):
    # Proxy the download from the hub
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{HUB_API_URL}/api/experiments/{experiment_id}/download")
        if resp.status_code == 200:
            return StreamingResponse(io.BytesIO(resp.content),
                                     media_type="application/zip",
                                     headers={
                                         "Content-Disposition": f"attachment; filename=experiment_{experiment_id}_results.zip"
                                     })
        else:
            raise HTTPException(status_code=resp.status_code, detail=f"Hub error: {resp.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download results: {e}") 
