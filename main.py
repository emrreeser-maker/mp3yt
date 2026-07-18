import os
import sys
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from yt_dlp import YoutubeDL

app = FastAPI(title="Cyber OS MP3 Extractor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- RENDER İÇİN YEREL FFMPEG ENTEGRASYONU ---
# Proje içindeki ffmpeg_bin klasörünün tam yolunu alıyoruz
FFMPEG_DIR = os.path.join(os.getcwd(), "ffmpeg_bin")
ffmpeg_path = os.path.join(FFMPEG_DIR, "ffmpeg")

# Render Linux altyapısında dosyaların çalıştırılabilmesi için okuma/yazma/çalıştırma izinlerini veriyoruz
if os.path.exists(ffmpeg_path):
    try:
        os.chmod(ffmpeg_path, 0o755)
        os.chmod(os.path.join(FFMPEG_DIR, "ffprobe"), 0o755)
        print(">>> Yerel FFmpeg izinleri başarıyla tanımlandı!")
    except Exception as e:
        print(f">>> İzin tanımlama uyarısı: {str(e)}")

# Sistem yürütme yoluna ekle
os.environ["PATH"] += os.pathsep + FFMPEG_DIR
# ---------------------------------------------

@app.post("/api/convert")
async def convert_video(payload: dict):
    video_url = payload.get("url")
    if not video_url:
        raise HTTPException(status_code=400, detail="URL_REQUIRED")
        
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': ffmpeg_path, # Doğrudan dosyayı işaret et
        'quiet': True
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        mp3_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.mp3")
        if os.path.exists(mp3_path):
            return {"success": True, "download_id": unique_id}
        else:
            raise HTTPException(status_code=500, detail="CONVERSION_FAILED")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{download_id}")
async def download_file(download_id: str):
    file_path = os.path.join(DOWNLOAD_DIR, f"{download_id}.mp3")
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename="cyber_audio.mp3", 
            media_type="audio/mpeg"
        )
    raise HTTPException(status_code=404, detail="FILE_NOT_FOUND")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
