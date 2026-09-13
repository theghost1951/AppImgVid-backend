from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os, uuid, jwt, datetime, traceback
from huggingface_hub import InferenceClient

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

JWT_SECRET = os.getenv("JWT_SECRET", "AppImgVid2026_Secret_Key_32_chars_long_secure_123")
HF_TOKEN = os.getenv("HF_TOKEN", "")
security = HTTPBearer()
os.makedirs("videos", exist_ok=True)
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

@app.get("/")
def root():
    return {"message": "FREE Backend Wan2.1", "hf": bool(HF_TOKEN)}

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
        raise HTTPException(401, f"Re-login: {e}")

    job_id = uuid.uuid4().hex[:8]
    input_path = f"videos/input_{job_id}.jpg"
    output_path = f"videos/{job_id}.mp4"

    try:
        with open(input_path, "wb") as f:
            f.write(image.file.read())

        print(f"Prompt: {motion_prompt}")
        print(f"Calling HF Wan model...")

        client = InferenceClient(token=HF_TOKEN)

        # Wan2.1 is free and supports image-to-video with prompt
        # Try free models in order
        models_to_try = [
            "Wan-AI/Wan2.1-I2V-14B-480P",
            "Wan-AI/Wan2.1-I2V-14B-720P",
        ]

        video_bytes = None
        last_err = ""
        for model_id in models_to_try:
            try:
                print(f"Trying {model_id}")
                # image_to_video with prompt
                result = client.image_to_video(
                    image=open(input_path, "rb"),
                    prompt=motion_prompt,
                    model=model_id,
                )
                # result can be bytes or file
                if isinstance(result, bytes):
                    video_bytes = result
                else:
                    # If it's a file path or object
                    video_bytes = open(result, "rb").read() if isinstance(result, str) else result
                print(f"Success with {model_id}, {len(video_bytes)} bytes")
                break
            except Exception as e:
                last_err = str(e)
                print(f"Model {model_id} failed: {last_err[:500]}")
                continue

        if not video_bytes:
            raise HTTPException(500, f"All HF models failed: {last_err[:500]}")

        with open(output_path, "wb") as f:
            f.write(video_bytes)

        if os.path.exists(input_path):
            os.remove(input_path)

            return {"job_id": job_id, "video_url": f"https://appimgvid-backend2026.onrender.com/videos/{job_id}.mp4"}

    except HTTPException:
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(500, str(e))
