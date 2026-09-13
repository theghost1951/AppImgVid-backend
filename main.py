from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime

app = FastAPI(title="AppImgVid Backend")

# Allow your Android app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret")
security = HTTPBearer()

# THIS IS THE FIX - Create videos folder and serve it
os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    return {"message": "AppImgVid Backend running", "docs": "/docs"}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "roger" and password == "AppImgVid2026":
        token = jwt.encode({"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/generate")
def generate(
    image: UploadFile = File(...),
    motion_prompt: str = Form(""),
    resolution: str = Form("1080"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Verify token
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    job_id = uuid.uuid4().hex[:8]
    filename = f"{job_id}.mp4"
    filepath = os.path.join("videos", filename)

    # CREATE A REAL FILE so 404 goes away - this is a 1-second valid MP4 header
    # Your app will now get 200 OK instead of 404, and show black video until we add AI
    with open(filepath, "wb") as f:
        # Minimal valid MP4 so ExoPlayer doesn't crash with 404
        f.write(bytes.fromhex("00000018667479706D703432000000006D70343269736F6D0000000866726565000002086D646174"))

    print(f"Generated {filename} for prompt: {motion_prompt}")
    return {"job_id": job_id, "video_url": f"/videos/{filename}", "thumb_url": f"/videos/{filename}"}

@app.get("/videos/{filename}")
def get_video(filename: str):
    path = os.path.join("videos", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Video not found - was Render restarted? Free Render deletes files on restart")
    return StaticFiles(directory="videos")
