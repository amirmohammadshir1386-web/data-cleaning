from fastapi import FastAPI, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import re, io, csv, collections

app = FastAPI(title="Persian Data Cleaning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
ARABIC_DIGITS = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩']

def clean_persian_text(text: str) -> str:
    # Character normalization
    text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه').replace('ؤ', 'و').replace('إ', 'ا').replace('أ', 'ا').replace('\u0640', '')
    # Remove Diacritics
    text = re.sub(r'[\u064B-\u0652\u0670]', '', text)
    # Remove URLs, Emails, Mentions, HTML, Emojis
    text = re.sub(r'<[^>]*>', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
    text = re.sub(r'@[\w\d_]+', '', text)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    # Semi-space (ZWNJ)
    zwnj = '\u200c'
    text = re.sub(r'\b(می|نمی)\s+', rf'\1{zwnj}', text)
    text = re.sub(r'\s+(ها|های|تر|ترین|ام|ات|اش|ایم|اید|اند)\b', rf'{zwnj}\1', text)
    # Digits
    for i in range(10):
        text = text.replace(str(i), PERSIAN_DIGITS[i]).replace(ARABIC_DIGITS[i], PERSIAN_DIGITS[i])
    # Spacing and punctuation
    text = re.sub(r'([!؟?.,،؛:]){2,}', r'\1', text)
    text = re.sub(r'\s+([!؟?.,،؛:])', r'\1', text)
    text = re.sub(r'([!؟?.,،؛:])([^\s\d!؟?.,،؛:])', r'\1 \2', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

class CleanRequest(BaseModel):
    text: str

@app.get("/")
def home():
    return {"status": "running", "docs": "/docs"}

@app.post("/api/v1/clean")
def clean_endpoint(req: CleanRequest):
    lines = [clean_persian_text(l) for l in req.text.split('\n') if l.strip()]
    seen, unique_lines = set(), []
    for l in lines:
        if l not in seen and len(l.split()) >= 3:
            seen.add(l)
            unique_lines.append(l)
    return {
        "cleaned_lines": unique_lines,
        "cleaned_text": "\n".join(unique_lines),
        "total_lines": len(unique_lines)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
