from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime, requests, time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret")
HF_TOKEN = os.getenv("HF_TOKEN", "")
security = HTTPBearer()

os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    return {"message": "AppImgVid FREE Backend (HuggingFace)", "hf_configured": bool(HF_TOKEN)}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "roger" and password == "AppImgVid2026":
        token = jwt.encode({"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid")

@app.post("/generate")
def generate(
    image: UploadFile = File(...),
    motion_prompt: str = Form("subtle motion"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="HF_TOKEN not set in Render")

    job_id = uuid.uuid4().hex[:8]
    input_path = f"videos/input_{job_id}.jpg"
    output_path = f"videos/{job_id}.mp4"

    try:
        # Save upload
        with open(input_path, "wb") as f:
            f.write(image.file.read())

        print(f"Job {job_id} prompt: {motion_prompt}")
        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}

        with open(input_path, "rb") as f:
            img_bytes = f.read()

        # HF free API needs retries - model cold starts
        video_bytes = None
        for i in range(6):
            print(f"HF attempt {i+1}...")
            resp = requests.post(API_URL, headers=headers, data=img_bytes, timeout=180)
            if resp.status_code == 200:
                video_bytes = resp.content
                print(f"Got video {len(video_bytes)} bytes")
                break
            elif resp.status_code == 503:
                print("Model loading, waiting 15s...")
                time.sleep(15)
                continue
            else:
                print(f"HF error {resp.status_code}: {resp.text[:500]}")
                raise HTTPException(status_code=500, detail=f"HF Error: {resp.text[:500]}")

        if not video_bytes:
            raise HTTPException(status_code=500, detail="HF model timeout, try again")

        with open(output_path, "wb") as f:
            f.write(video_bytes)

        if os.path.exists(input_path):
            os.remove(input_path)

        return {"job_id": job_id, "video_url": f"/videos/{job_id}.mp4", "thumb_url": f"/videos/{job_id}.mp4"}

    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
