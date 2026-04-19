from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from io import BytesIO
from printer import Printer

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

printer = Printer("SII_RP_F10_G10")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/print/text")
async def print_text(text: str = Form(...), align: str = Form("left")):
    printer.print_text(text, align)
    return JSONResponse({"status": "ok"})


@app.post("/print/image")
async def print_image(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="No file uploaded")
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read image: {e}")
    printer.print_image(image)
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
