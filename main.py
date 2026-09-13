from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime, requests, time, traceback

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret")
HF_TOKEN = os.getenv("HF_TOKEN", "")
security = HTTPBearer()
os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    return {"message": "FREE Backend", "hf": bool(HF_TOKEN), "hf_len": len(HF_TOKEN) if HF_TOKEN else 0}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "roger" and password == "AppImgVid2026":
        token = jwt.encode({"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(401, "Invalid")

@app.post("/generate")
def generate(image: UploadFile = File(...), motion_prompt: str = Form(""), credentials: HTTPAuthorizationCredentials = Depends(security)):
    print(f"Generate called, prompt={motion_prompt}")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        print(f"JWT OK for {payload.get('user')}")
    except Exception as e:
        print(f"JWT FAIL: {e}")
        print(traceback.format_exc())
        raise HTTPException(401, f"Token invalid, please re-login: {e}")

    if not HF_TOKEN:
        raise HTTPException(500, "HF_TOKEN missing")

    job_id = uuid.uuid4().hex[:8]
    input_path = f"videos/input_{job_id}.jpg"
    output_path = f"videos/{job_id}.mp4"

    try:
        with open(input_path, "wb") as f:
            f.write(image.file.read())
        print(f"Saved {input_path}")

        API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-video-diffusion-img2vid-xt"
        headers = {"Authorization": f"Bearer {HF_TOKEN.strip()}"}
        
        with open(input_path, "rb") as f:
            img_bytes = f.read()

        for i in range(4):
            print(f"HF try {i+1}")
            r = requests.post(API_URL, headers=headers, data=img_bytes, timeout=180)
            print(f"HF status {r.status_code}")
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                print(f"Saved video {len(r.content)} bytes")
                os.remove(input_path)
                return {"job_id": job_id, "video_url": f"/videos/{job_id}.mp4"}
            elif r.status_code == 503:
                print(f"HF loading: {r.text[:200]}")
                time.sleep(20)
                continue
            else:
                print(f"HF fail: {r.text[:500]}")
                raise HTTPException(500, f"HF {r.status_code}: {r.text[:500]}")

        raise HTTPException(500, "HF timeout after retries")

    except HTTPException:
        raise
    except Exception as e:
        print(f"CRASH: {e}")
        print(traceback.format_exc())
        raise HTTPException(500, str(e))
