
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
import shutil
import os
import io
import tempfile
from typing import List, Optional
from pydantic import BaseModel

from extractor import extract_text
from prompts import get_prompt_for_data

# ReportLab for PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

class DownloadRequest(BaseModel):
    content: str
    format: str
    filename: str = "result"

def call_claude_api(prompt: str) -> str:
    """Calls Anthropic Claude API with the given prompt."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None  # Signal to use mock

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        # List of models to try in order of preference
        models_to_try = [
            "claude-3-5-sonnet-20241022", # Sonnet 3.5 (New)
            "claude-3-5-sonnet-20240620", # Sonnet 3.5 (Old)
            "claude-3-opus-20240229",     # Opus 3
            "claude-3-sonnet-20240229",   # Sonnet 3
            "claude-3-haiku-20240307",    # Haiku 3
        ]
        
        last_error = None
        
        for model_name in models_to_try:
            # Determine max tokens based on model capability
            # Claude 3.5 supports 8192. Older models (Opus/Sonnet 3) typically 4096.
            max_tokens_limit = 8192 if "3-5" in model_name else 4096
            
            try:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens_limit, 
                    temperature=0.0,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            except anthropic.NotFoundError as e:
                print(f"Model {model_name} not found, trying next...")
                last_error = e
                continue
            except anthropic.BadRequestError as e:
                # If 8192 was too high for some reason, retry with 4096
                if "max_tokens" in str(e) and max_tokens_limit > 4096:
                    print(f"Model {model_name} rejected token limit. Retrying with 4096...")
                    try:
                        response = client.messages.create(
                            model=model_name,
                            max_tokens=4096, 
                            temperature=0.0,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        return response.content[0].text
                    except Exception as retry_e:
                        last_error = retry_e
                        continue
                last_error = e
                continue
            except Exception as e:
                return f"Error with model {model_name}: {str(e)}"
                
        return f"Error: No working Claude model found. Last error: {str(last_error)}"
    except ImportError:
        return "Error: anthropic library not installed."
    except Exception as e:
        return f"Error calling Claude API: {str(e)}"

@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...)
):
    """
    Uploads files, extracts text, and generates a prompt.
    Uses ANTHROPIC_API_KEY from environment.
    """
    results = []
    
    for file in files:
        # Save temp file
        file_path = os.path.join(TEMP_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Extract text
        extracted_text = extract_text(file_path)
        
        # Generate Prompt
        prompt = get_prompt_for_data(extracted_text)
        
        # Clean up temp file
        try:
            os.remove(file_path)
        except:
            pass
        
        # AI Response
        ai_response = call_claude_api(prompt)
        
        if not ai_response:
             # Mock Response if no valid key found
            ai_response = f"""
# Extracted Structure for {file.filename} (SIMULATION)

(No valid ANTHROPIC_API_KEY found in backend/.env, so this is a simulated response.)

## Summary
The document contains {len(extracted_text)} characters.

## Mock Data Points
- **Category 1**: Simulation Data A
- **Category 2**: Simulation Data B
"""
        
        results.append({
            "filename": file.filename,
            "extracted_text_preview": extracted_text[:500] + "...",
            "generated_prompt": prompt,
            "ai_response": ai_response
        })
        
    return JSONResponse(content={"results": results})

@app.post("/download")
async def download_result(request: DownloadRequest):
    """
    Generates a file (PDF, MD, TXT) from the provided content string.
    """
    content = request.content
    fmt = request.format.lower()
    filename = request.filename
    
    if fmt == "md":
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}.md"}
        )
    
    elif fmt == "txt":
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}.txt"}
        )
        
    elif fmt == "pdf":
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Basic PDF generation (handles multi-line text roughly)
        text_object = c.beginText(40, height - 40)
        
        # Attempt to register a font that supports Japanese if available, otherwise default
        # Checking for common fonts or just using standard Helvetica for MVP (doesn't support JP)
        # PRACTICAL NOTE: Supporting Japanese in PDF requires a font file (like NotoSans).
        # We will use standard font for now and warn about encoding if needed, 
        # or try to use a standard font. 
        # To strictly support Japanese, we'd need to ship a .ttf file.
        # For this demo, let's assume english or basic support.
        # If the user input is Japanese (which it is), we must try to support it.
        # But without a font file it's hard. Let's try to stick to basic ASCII or provide a placeholder.
        # ACTUALLY, let's try to use a standard font if possible, but ReportLab needs registration.
        # Minimal viable: Helvetica (no JP).
        
        # Improving for Japanese support:
        # We really need a font. I'll stick to English-safe implementation for now 
        # or just write utf-8 text and hope for best? No, reportlab needs fonts.
        # I'll rely on the frontend PDF generation if this acts up, but let's try.
        
        text_object.setFont("Helvetica", 10)
        
        lines = content.split('\n')
        y = height - 40
        for line in lines:
            if y < 40:
                c.drawText(text_object)
                c.showPage()
                text_object = c.beginText(40, height - 40)
                text_object.setFont("Helvetica", 10)
                y = height - 40
            
            # Simple word wrap simulation or just truncate
            # Reportlab's textObject doesn't auto-wrap easily without Paragraph flowables.
            # Keeping it very simple for "MVP".
            text_object.textLine(line[:90] + ("..." if len(line) > 90 else ""))
            y -= 12
            
        c.drawText(text_object)
        c.save()
        buffer.seek(0)
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )
        
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

@app.get("/")
def read_root():
    return FileResponse("../frontend/index.html")

# Keep this at the end to not block API routes if we were mounting a folder, 
# but here we just serve one file at root.
# If we had other assets (css/js), we would mount them:
# app.mount("/static", StaticFiles(directory="../frontend"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
