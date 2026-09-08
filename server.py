from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import trimesh
import numpy as np
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

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp:
        temp.write(await file.read())
        temp_path = temp.name

    try:
        unique_name = f"{uuid.uuid4()}{ext}"
        dest_path = os.path.join("static", "output", unique_name)
        
        with open(dest_path, "wb") as dest:
            with open(temp_path, "rb") as src:
                dest.write(src.read())

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

@app.post("/voxelize")
async def voxelize_model(data: dict):
    model_url = data.get("model_url")
    resolution = int(data.get("resolution", 32))
    
    if not model_url:
        return {"success": False, "error": "No model URL provided."}
    
    file_path = os.path.join(".", model_url.lstrip("/"))
    if not os.path.exists(file_path):
        return {"success": False, "error": "Model file not found on server."}

    try:
        mesh = trimesh.load(file_path, force='mesh')
        
        # Force conversion of visual materials to vertex/face colors if possible
        if hasattr(mesh.visual, 'to_color'):
            try:
                mesh.visual = mesh.visual.to_color()
            except Exception as e:
                print("Visual to_color conversion note:", e)

        to_voxel = mesh.voxelized(pitch=mesh.extents.max() / resolution)
        matrix = to_voxel.matrix
        
        indices = np.argwhere(matrix)
        if len(indices) == 0:
            return {"success": False, "error": "Voxel grid is empty. Try a lower resolution or different model."}

        # Get voxel center coordinates
        if hasattr(to_voxel, 'points') and len(to_voxel.points) == len(indices):
            centers = to_voxel.points
        else:
            pitch = to_voxel.pitch
            transform = to_voxel.transform
            centers = (indices * pitch) @ transform[:3, :3].T + transform[:3, 3]

        colors = None
        has_colors = False

        try:
            # Check for direct vertex colors
            if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
                vertex_colors = mesh.visual.vertex_colors[:, :3]
                _, _, face_ids = mesh.nearest.on_surface(centers)
                tri_vertices = mesh.faces[face_ids]
                colors = np.mean(vertex_colors[tri_vertices], axis=1)
                has_colors = True

            # Check for face colors if vertex colors aren't present
            elif hasattr(mesh.visual, 'face_colors') and mesh.visual.face_colors is not None:
                face_colors = mesh.visual.face_colors[:, :3]
                _, _, face_ids = mesh.nearest.on_surface(centers)
                colors = face_colors[face_ids]
                has_colors = True
                
        except Exception as col_err:
            print("Color mapping error details:", col_err)

        voxel_coords = []
        for i, idx in enumerate(indices):
            voxel_item = {
                "x": int(idx[0]),
                "y": int(idx[1]),
                "z": int(idx[2])
            }
            if has_colors and colors is not None and i < len(colors):
                c = colors[i]
                voxel_item["color"] = [int(c[0]), int(c[1]), int(c[2])]
            else:
                # Neutral stone/grey fallback tone
                voxel_item["color"] = [120, 120, 120] 
            
            voxel_coords.append(voxel_item)

        return {
            "success": True, 
            "total_voxels": len(voxel_coords),
            "voxels": voxel_coords
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)