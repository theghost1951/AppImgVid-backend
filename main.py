from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os, uuid, jwt, datetime, glob

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret_Key_32_chars_long_secure_123")
HF_TOKEN = os.getenv("HF_TOKEN", "")
BASE_URL = "https://appimgvid-backend2026.onrender.com"
security = HTTPBearer()
os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    files = glob.glob("videos/*.mp4")
    links = [f"{BASE_URL}/videos/{os.path.basename(f)}" for f in files[-5:]]
    return {"message": "FREE Backend", "hf": bool(HF_TOKEN), "latest_videos": links}

@app.get("/latest")
def latest():
    files = sorted(glob.glob("videos/*.mp4"), key=os.path.getmtime, reverse=True)
    if not files:
        return {"error": "no videos yet"}
    return FileResponse(files[0], media_type="video/mp4")

@app.get("/history")
def history(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(401, "Re-login")
    vids = []
    for f in sorted(glob.glob("videos/*.mp4"), reverse=True)[:10]:
        name = os.path.basename(f)
        vids.append({"job_id": name.replace(".mp4",""), "video_url": f"{BASE_URL}/videos/{name}"})
    return {"videos": vids}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "roger" and password == "AppImgVid2026":
        token = jwt.encode({"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(401, "Invalid")

@app.post("/generate")
def generate(image: UploadFile = File(...), motion_prompt: str = Form(""), credentials: HTTPAuthorizationCredentials = Depends(security)):
    from huggingface_hub import InferenceClient
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(401, "Re-login")
    job_id = uuid.uuid4().hex[:8]
    input_path = f"videos/input_{job_id}.jpg"
    output_path = f"videos/{job_id}.mp4"
    with open(input_path, "wb") as f:
        f.write(image.file.read())
    print(f"Prompt: {motion_prompt}")
    client = InferenceClient(token=HF_TOKEN)
    try:
        result = client.image_to_video(image=input_path, prompt=motion_prompt or "gentle lowering motion", model="Wan-AI/Wan2.1-I2V-14B-720P")
        data = result if isinstance(result, bytes) else open(result, "rb").read() if isinstance(result, str) else result
        with open(output_path, "wb") as f:
            f.write(data)
        os.remove(input_path)
        print(f"SAVED {output_path} {len(data)} bytes")
        return {"job_id": job_id, "video_url": f"{BASE_URL}/videos/{job_id}.mp4"}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, str(e))
