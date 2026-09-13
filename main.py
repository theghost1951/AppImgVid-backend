from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime, requests, time, traceback

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret_Key_32_chars_long_secure_123")
HF_TOKEN = os.getenv("HF_TOKEN", "")
security = HTTPBearer()
os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    return {"message": "FREE Backend v2", "hf": bool(HF_TOKEN), "hf_len": len(HF_TOKEN) if HF_TOKEN else 0}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == "roger" and password == "AppImgVid2026":
        token = jwt.encode({"user": username, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    raise HTTPException(401, "Invalid")

@app.post("/generate")
def generate(image: UploadFile = File(...), motion_prompt: str = Form(""), credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise HTTPException(401, f"Re-login needed: {e}")

    if not HF_TOKEN:
        raise HTTPException(500, "HF_TOKEN missing")

    job_id = uuid.uuid4().hex[:8]
    input_path = f"videos/input_{job_id}.jpg"
    output_path = f"videos/{job_id}.mp4"

    try:
        with open(input_path, "wb") as f:
            f.write(image.file.read())

        # NEW HF ROUTER ADDRESS (old one is dead)
        API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-video-diffusion-img2vid-xt"
        headers = {"Authorization": f"Bearer {HF_TOKEN.strip()}"}
        
        with open(input_path, "rb") as f:
            img_bytes = f.read()

        print(f"Calling NEW HF endpoint {API_URL}")

        for i in range(5):
            print(f"HF try {i+1}")
            try:
                r = requests.post(API_URL, headers=headers, data=img_bytes, timeout=180)
                print(f"HF status {r.status_code}")
                if r.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(r.content)
                    print(f"Video saved {len(r.content)}")
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    return {"job_id": job_id, "video_url": f"/videos/{job_id}.mp4"}
                elif r.status_code in [503, 429]:
                    print(f"HF busy/loading: {r.text[:200]}")
                    time.sleep(20)
                    continue
                else:
                    print(f"HF error {r.text[:500]}")
                    # Try fallback model if XT fails
                    if "not found" in r.text.lower() or r.status_code == 404:
                        API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-video-diffusion-img2vid"
                        print(f"Trying fallback {API_URL}")
                        time.sleep(5)
                        continue
                    raise HTTPException(500, f"HF {r.status_code}: {r.text[:400]}")
            except requests.exceptions.ConnectionError as ce:
                print(f"Connection error {ce}, retry in 10s")
                time.sleep(10)
                continue

        raise HTTPException(500, "HF timeout")

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, str(e))
