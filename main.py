import trimesh
import os

def load_3d_model(file_path):
    """
    Loads a 3D model using trimesh and prints out its basic properties.
    """
    # Check if the file actually exists before trying to load it
    if not os.path.exists(file_path):
        print(f"❌ Error: The file '{file_path}' was not found in the directory.")
        print("Please place a .obj or .stl model in your project folder and update the filename.")
        return None

    print(f"⏳ Loading 3D model from '{file_path}'...")
    
    # trimesh.load automatically detects file type (.obj, .stl, .gltf, etc.)
    mesh = trimesh.load(file_path)
    
    print("\n✨ Model Loaded Successfully!")
    print(f"----------------------------------------")
    print(f"🔹 Total Vertices (points): {len(mesh.vertices)}")
    print(f"🔹 Total Faces (triangles): {len(mesh.faces)}")
    print(f"🔹 Is the mesh watertight (solid/closed)? {mesh.is_watertight}")
    print(f"🔹 Bounding Box Size (Width, Height, Depth): {mesh.extents}")
    print(f"----------------------------------------")
    
    return mesh

if __name__ == "__main__":
    # Change 'model.obj' to match the actual name of your file
    target_file = "model.obj"
    
    # Run the function
    my_mesh = load_3d_model(target_file)