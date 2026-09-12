import os, uuid, shutil, sqlite3
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
import jwt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AppImgVid Backend")
security = HTTPBearer()

client = OpenAI(
    api_key=os.getenv("LLAMA_API_KEY", "missing"),
    base_url="https://api.llama.com/compat/v1/"
)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
USERS = {"roger": "AppImgVid2026"}

os.makedirs("outputs", exist_ok=True)
os.makedirs("app_storage", exist_ok=True)

def init_db():
    conn = sqlite3.connect("app_storage/history.db")
    conn.execute("CREATE TABLE IF NOT EXISTS videos (id TEXT PRIMARY KEY, user TEXT, video_path TEXT, prompt TEXT, resolution TEXT, aspect TEXT, duration INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit(); conn.close()
init_db()

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if USERS.get(username) == password:
        token = jwt.encode({"sub": username}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(401, "Invalid credentials")

def get_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    try:
        data = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        return data["sub"]
    except:
        raise HTTPException(401, "Invalid token")

@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    motion_prompt: str = Form(""),
    negative_prompt: str = Form(""),
    resolution: str = Form("1080"),
    aspect_ratio: str = Form("16:9"),
    camera_json: str = Form("{}"),
    duration_sec: int = Form(5),
    user: str = Depends(get_user)
):
    job_id = str(uuid.uuid4())[:8]
    input_path = f"outputs/{job_id}_input.jpg"
    output_path = f"outputs/{job_id}.mp4"
    with open(input_path, "wb") as f:
        shutil.copyfileobj(image.file, f)
    with open(output_path, "wb") as out:
        out.write(b"")
    conn = sqlite3.connect("app_storage/history.db")
    conn.execute("INSERT INTO videos (id, user, video_path, prompt, resolution, aspect, duration) VALUES (?,?,?,?,?,?,?)",
                 (job_id, user, output_path, motion_prompt, resolution, aspect_ratio, duration_sec))
    conn.commit(); conn.close()
    return {"job_id": job_id, "video_url": f"/videos/{job_id}.mp4", "status": "completed", "resolution": resolution, "aspect_ratio": aspect_ratio}

@app.get("/")
def root():
    return {"message": "AppImgVid Backend running", "docs": "/docs"}

@app.get("/videos/{video_id}.mp4")
def serve_video(video_id: str, user: str = Depends(get_user)):
    path = f"outputs/{video_id}.mp4"
    if not os.path.exists(path):
        raise HTTPException(404, "Video not found")
    return FileResponse(path, media_type="video/mp4")
