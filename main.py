from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime, requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret")
security = HTTPBearer()

os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# Download a real video ONCE so your backend owns it
BUNNY_PATH = "videos/bunny.mp4"
if not os.path.exists(BUNNY_PATH):
    try:
        print("Downloading sample video...")
        r = requests.get("https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4", timeout=30)
        open(BUNNY_PATH, "wb").write(r.content)
        print("Sample saved")
    except Exception as e:
        print(f"Download failed: {e}")

@app.get("/")
def root():
    return {"message": "AppImgVid Backend running", "bunny_exists": os.path.exists(BUNNY_PATH)}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "roger" and password == "AppImgVid2026":
        token = jwt.encode({"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid")

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
    # Return YOUR OWN backend video - no more Google 403
    return {"job_id": job_id, "video_url": "/videos/bunny.mp4", "thumb_url": "/videos/bunny.mp4"}
