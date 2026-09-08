from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import trimesh
import tempfile
import os
import uuid

app = FastAPI(title="3D to Minecraft Voxel Converter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/output", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.post("/upload")
async def upload_model(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in ['.glb', '.gltf', '.obj', '.stl']:
        return {"success": False, "error": f"File type '{ext[1:]}' not supported"}

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp:
        temp.write(await file.read())
        temp_path = temp.name

    try:
        # Save file permanently into static/output so the frontend can load it via URL
        unique_name = f"{uuid.uuid4()}{ext}"
        dest_path = os.path.join("static", "output", unique_name)
        
        with open(dest_path, "wb") as dest:
            with open(temp_path, "rb") as src:
                dest.write(src.read())

        # Load mesh via trimesh to extract stats
        mesh = trimesh.load(dest_path, force='mesh')
        
        stats = {
            "filename": file.filename,
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "is_watertight": bool(mesh.is_watertight),
            "bounds": mesh.extents.tolist(),
            "model_url": f"/static/output/{unique_name}"
        }
        
        return {"success": True, "data": stats}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)