import asyncio

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.gzip import GZipMiddleware

from processing import PRESETS, process_image

app = FastAPI()

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024


@app.post("/process")
async def process(
    image: UploadFile = File(...),
    preset: str = Form(...),
):
    if preset not in PRESETS:
        raise HTTPException(400, f"Invalid preset. Choose from: {list(PRESETS.keys())}")

    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Unsupported image format. Use JPG, PNG, or WebP.")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "Image too large. Maximum 10MB.")

    try:
        svg_content = await asyncio.to_thread(process_image, image_bytes, preset)
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="contour_{preset}.svg"'},
    )


@app.get("/presets")
def get_presets():
    return PRESETS
