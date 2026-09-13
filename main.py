from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime

app = FastAPI(title="AppImgVid Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret")
security = HTTPBearer()

os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    return {"message": "AppImgVid Backend running"}

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
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    job_id = uuid.uuid4().hex[:8]
    
    # RETURN A REAL SAMPLE VIDEO THAT WILL PLAY - to prove pipeline works
    # Later we replace this with your AI video
    sample_video = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    
    print(f"Generated {job_id} for prompt: {motion_prompt}")
    return {"job_id": job_id, "video_url": sample_video, "thumb_url": sample_video}
