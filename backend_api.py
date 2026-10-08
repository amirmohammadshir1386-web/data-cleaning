"""
FastAPI Backend for Persian Text Data Cleaning and Analysis
Based on the architecture of amirmohammadshir1386-web/data-cleaning repository.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response, JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import re
import io
import csv
import json
import collections

# Optional integration with Hazm if installed
try:
    import hazm as hz
    HAS_HAZM = True
    _normalizer = hz.Normalizer()
except ImportError:
    HAS_HAZM = False
    _normalizer = None

app = FastAPI(
    title="Persian Data Cleaning API",
    description="Backend API for Persian text normalization, noise removal, deduplication, and corpus analysis.",
    version="1.0.0"
)

# Enable CORS for frontend web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Core NLP & Cleaning Engine (cleaner.py)
# ==========================================

PERSIAN_DIGITS = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']
ARABIC_DIGITS = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩']

def normalize_persian_chars(text: str) -> str:
    """Normalize Arabic characters to standard Persian and strip kashida."""
    replacements = {
        'ي': 'ی',
        'ك': 'ک',
        'ة': 'ه',
        'ؤ': 'و',
        'إ': 'ا',
        'أ': 'ا',
        'ء': '',
        '\u0640': '',  # Kashida
    }
    for orig, target in replacements.items():
        text = text.replace(orig, target)
    return text

def standardize_digits(text: str, to_persian: bool = True) -> str:
    """Standardize numbers to Persian or English digits."""
    if to_persian:
        for i in range(10):
            text = text.replace(str(i), PERSIAN_DIGITS[i])
            text = text.replace(ARABIC_DIGITS[i], PERSIAN_DIGITS[i])
    else:
        for i in range(10):
            text = text.replace(PERSIAN_DIGITS[i], str(i))
            text = text.replace(ARABIC_DIGITS[i], str(i))
    return text

def remove_diacritics(text: str) -> str:
    """Remove Arabic/Persian diacritics (Fatha, Damma, Kasra, Tanwin, Tashdid, Sukun)."""
    return re.sub(r'[\u064B-\u0652\u0670]', '', text)

def fix_semi_spaces(text: str) -> str:
    """Standardize Zero-Width Non-Joiner (ZWNJ / نیم‌فاصله) for affixes."""
    zwnj = '\u200c'
    # Prefixes (می / نمی)
    text = re.sub(r'\b(می|نمی)\s+', rf'\1{zwnj}', text)
    # Suffixes (ها، های، تر، ترین، ام، ات، اش، ایم، اید، اند)
    text = re.sub(r'\s+(ها|های|تر|ترین|ام|ات|اش|ایم|اید|اند)\b', rf'{zwnj}\1', text)
    # Deduplicate ZWNJ
    text = re.sub(rf'{zwnj}{{2,}}', zwnj, text)
    return text

def remove_html_tags(text: str) -> str:
    return re.sub(r'<[^>]*>', ' ', text)

def remove_urls(text: str) -> str:
    return re.sub(r'https?://\S+|www\.\S+', '', text, flags=re.IGNORECASE)

def remove_emails(text: str) -> str:
    return re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)

def remove_mentions(text: str) -> str:
    return re.sub(r'@[\w\d_]+', '', text)

def remove_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002600-\U000026FF"  # Miscellaneous Symbols
        "\U00002700-\U000027BF"  # Dingbats
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def clean_punctuation(text: str) -> str:
    # Deduplicate punctuation
    text = re.sub(r'([!؟?.,،؛:]){2,}', r'\1', text)
    # Proper spacing: remove space before punctuation, add space after
    text = re.sub(r'\s+([!؟?.,،؛:])', r'\1', text)
    text = re.sub(r'([!؟?.,،؛:])([^\s\d!؟?.,،؛:])', r'\1 \2', text)
    # Collapse multiple whitespaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def clean_hashtags(text: str) -> str:
    return re.sub(r'#([\w\u0600-\u06FF]+)', lambda m: m.group(1).replace('_', ' '), text)

def is_valid_sentence(text: str, min_words: int = 3, min_persian_ratio: float = 0.5) -> bool:
    """Validate sentence viability and Persian content dominance."""
    words = text.strip().split()
    if len(words) < min_words:
        return False
    persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    total_chars = len(re.sub(r'\s', '', text))
    if total_chars == 0:
        return False
    return (persian_chars / total_chars) >= min_persian_ratio

# ==========================================
# Pydantic Request & Response Schemas
# ==========================================

class CleaningOptions(BaseModel):
    normalize_chars: bool = Field(default=True, description="Convert Arabic yeh/kaf to Persian")
    semi_space: bool = Field(default=True, description="Standardize ZWNJ for Persian affixes")
    persian_digits: bool = Field(default=True, description="Convert numbers to Persian digits")
    remove_diacritics: bool = Field(default=True, description="Remove vowels and accents")
    remove_urls: bool = Field(default=True, description="Remove web URLs and links")
    remove_emails: bool = Field(default=True, description="Remove email addresses")
    remove_mentions: bool = Field(default=True, description="Remove @mentions")
    remove_html: bool = Field(default=True, description="Strip HTML tags")
    remove_emojis: bool = Field(default=True, description="Remove emojis and pictorial symbols")
    clean_punctuation: bool = Field(default=True, description="Standardize punctuation spacing")
    clean_hashtags: bool = Field(default=True, description="Convert hashtags into plain words")
    deduplicate: bool = Field(default=True, description="Remove duplicate sentences/lines")
    filter_short: bool = Field(default=True, description="Filter out lines with fewer than 3 words")
    validate_sentence: bool = Field(default=True, description="Verify Persian language dominance")

class CleanTextRequest(BaseModel):
    text: str = Field(..., description="Raw Persian text to clean")
    options: Optional[CleaningOptions] = Field(default_factory=CleaningOptions)

class CleanResponse(BaseModel):
    cleaned_lines: List[str]
    cleaned_text: str
    raw_lines_count: int
    cleaned_lines_count: int
    duplicates_removed_count: int
    raw_characters_count: int
    cleaned_characters_count: int
    noise_reduction_percent: float

class AnalysisReport(BaseModel):
    total_lines: int
    total_words: int
    total_characters: int
    unique_vocabulary_count: int
    avg_sentence_length: float
    avg_word_length: float
    top_words: List[Dict[str, Any]]
    top_characters: List[Dict[str, Any]]
    hashtags_found: Dict[str, int]

# ==========================================
# Core Pipeline Processing Logic
# ==========================================

def execute_cleaning_pipeline(raw_text: str, options: CleaningOptions) -> tuple:
    lines = raw_text.split('\n')
    processed_lines = []
    hashtag_counter = collections.Counter()

    for raw_line in lines:
        line = raw_line

        # Count hashtags before stripping
        tags = re.findall(r'#[\w\u0600-\u06FF_]+', line)
        for t in tags:
            hashtag_counter[t] += 1

        if options.remove_html:
            line = remove_html_tags(line)
        if options.remove_urls:
            line = remove_urls(line)
        if options.remove_emails:
            line = remove_emails(line)
        if options.remove_mentions:
            line = remove_mentions(line)
        if options.remove_emojis:
            line = remove_emojis(line)
        if options.clean_hashtags:
            line = clean_hashtags(line)
        if options.normalize_chars:
            line = normalize_persian_chars(line)
        if options.remove_diacritics:
            line = remove_diacritics(line)
        if options.semi_space:
            line = fix_semi_spaces(line)
        if options.persian_digits:
            line = standardize_digits(line, to_persian=True)
        if options.clean_punctuation:
            line = clean_punctuation(line)

        line = line.strip()

        if line:
            if options.filter_short and len(line.split()) < 3:
                continue
            if options.validate_sentence and not is_valid_sentence(line):
                continue
            processed_lines.append(line)

    # Deduplication
    final_lines = []
    duplicates_count = 0
    if options.deduplicate:
        seen = set()
        for l in processed_lines:
            if l not in seen:
                seen.add(l)
                final_lines.append(l)
            else:
                duplicates_count += 1
    else:
        final_lines = processed_lines

    return final_lines, duplicates_count, hashtag_counter

def compute_corpus_analysis(lines: List[str], hashtag_counter: collections.Counter) -> AnalysisReport:
    clean_text = "\n".join(lines)
    words = clean_text.split()
    total_words = len(words)
    total_chars = len(clean_text)

    # Word frequencies
    word_counter = collections.Counter()
    for w in words:
        w_clean = re.sub(r'[!؟?.,،؛:]', '', w)
        if len(w_clean) > 1:
            word_counter[w_clean] += 1

    # Char frequencies
    char_counter = collections.Counter()
    for ch in clean_text:
        if ch not in (' ', '\n'):
            char_counter[ch] += 1

    unique_vocab = len(word_counter)
    avg_sent_len = round(total_words / len(lines), 2) if lines else 0.0
    
    char_only_len = len(re.sub(r'\s', '', clean_text))
    avg_word_len = round(char_only_len / total_words, 2) if total_words > 0 else 0.0

    top_words = [
        {"word": w, "count": cnt, "percentage": round((cnt / total_words) * 100, 2) if total_words else 0}
        for w, cnt in word_counter.most_common(25)
    ]

    top_chars = [
        {"char": ch if ch != '\u200c' else 'نیم‌فاصله (ZWNJ)', "count": cnt, "percentage": round((cnt / total_chars) * 100, 2) if total_chars else 0}
        for ch, cnt in char_counter.most_common(20)
    ]

    return AnalysisReport(
        total_lines=len(lines),
        total_words=total_words,
        total_characters=total_chars,
        unique_vocabulary_count=unique_vocab,
        avg_sentence_length=avg_sent_len,
        avg_word_length=avg_word_len,
        top_words=top_words,
        top_characters=top_chars,
        hashtags_found=dict(hashtag_counter)
    )

# ==========================================
# API Endpoints
# ==========================================

@app.get("/")
def root():
    return {
        "service": "Persian Data Cleaning & Normalization API",
        "repository": "amirmohammadshir1386-web/data-cleaning",
        "status": "online",
        "hazm_available": HAS_HAZM,
        "docs_url": "/docs"
    }

@app.post("/api/v1/clean", response_model=CleanResponse)
def clean_text(req: CleanTextRequest):
    """Clean raw text payload using configured NLP pipeline rules."""
    final_lines, dup_count, _ = execute_cleaning_pipeline(req.text, req.options)
    
    raw_chars = len(req.text)
    clean_str = "\n".join(final_lines)
    clean_chars = len(clean_str)
    
    reduction = round(((raw_chars - clean_chars) / raw_chars) * 100, 2) if raw_chars > 0 else 0.0

    return CleanResponse(
        cleaned_lines=final_lines,
        cleaned_text=clean_str,
        raw_lines_count=len(req.text.split('\n')),
        cleaned_lines_count=len(final_lines),
        duplicates_removed_count=dup_count,
        raw_characters_count=raw_chars,
        cleaned_characters_count=clean_chars,
        noise_reduction_percent=reduction
    )

@app.post("/api/v1/upload", response_model=CleanResponse)
async def upload_and_clean_file(
    file: UploadFile = File(...),
    normalize_chars: bool = Form(True),
    semi_space: bool = Form(True),
    persian_digits: bool = Form(True),
    remove_diacritics_flag: bool = Form(True),
    remove_urls_flag: bool = Form(True),
    remove_emails_flag: bool = Form(True),
    remove_mentions_flag: bool = Form(True),
    remove_html_flag: bool = Form(True),
    remove_emojis_flag: bool = Form(True),
    clean_punctuation_flag: bool = Form(True),
    clean_hashtags_flag: bool = Form(True),
    deduplicate: bool = Form(True),
    filter_short: bool = Form(True),
    validate_sentence: bool = Form(True)
):
    """Upload a file (.txt, .csv, .json), clean it, and return processed data."""
    content = await file.read()
    try:
        raw_text = content.decode('utf-8')
    except UnicodeDecodeError:
        raw_text = content.decode('latin-1')

    # If CSV, extract text column if possible
    if file.filename.endswith('.csv'):
        try:
            reader = csv.reader(io.StringIO(raw_text))
            rows = [row[0] for row in reader if row]
            raw_text = "\n".join(rows)
        except Exception:
            pass

    options = CleaningOptions(
        normalize_chars=normalize_chars,
        semi_space=semi_space,
        persian_digits=persian_digits,
        remove_diacritics=remove_diacritics_flag,
        remove_urls=remove_urls_flag,
        remove_emails=remove_emails_flag,
        remove_mentions=remove_mentions_flag,
        remove_html=remove_html_flag,
        remove_emojis=remove_emojis_flag,
        clean_punctuation=clean_punctuation_flag,
        clean_hashtags=clean_hashtags_flag,
        deduplicate=deduplicate,
        filter_short=filter_short,
        validate_sentence=validate_sentence
    )

    final_lines, dup_count, _ = execute_cleaning_pipeline(raw_text, options)
    clean_str = "\n".join(final_lines)
    raw_chars = len(raw_text)
    clean_chars = len(clean_str)
    reduction = round(((raw_chars - clean_chars) / raw_chars) * 100, 2) if raw_chars > 0 else 0.0

    return CleanResponse(
        cleaned_lines=final_lines,
        cleaned_text=clean_str,
        raw_lines_count=len(raw_text.split('\n')),
        cleaned_lines_count=len(final_lines),
        duplicates_removed_count=dup_count,
        raw_characters_count=raw_chars,
        cleaned_characters_count=clean_chars,
        noise_reduction_percent=reduction
    )

@app.post("/api/v1/analyze", response_model=AnalysisReport)
def analyze_text(req: CleanTextRequest):
    """Compute detailed corpus metrics on provided text (matching analyzer.py)."""
    final_lines, _, hashtag_counter = execute_cleaning_pipeline(req.text, req.options)
    return compute_corpus_analysis(final_lines, hashtag_counter)

@app.post("/api/v1/export/csv")
def export_csv(req: CleanTextRequest):
    """Download cleaned text as final.csv (with UTF-8 BOM)."""
    final_lines, _, _ = execute_cleaning_pipeline(req.text, req.options)
    
    output = io.StringIO()
    # Write UTF-8 BOM for Persian Excel support
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(["id", "cleaned_text"])
    for idx, line in enumerate(final_lines, start=1):
        writer.writerow([idx, line])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=final.csv"}
    )

@app.post("/api/v1/export/report")
def export_report(req: CleanTextRequest):
    """Download analyzer.txt statistical report."""
    final_lines, _, hashtag_counter = execute_cleaning_pipeline(req.text, req.options)
    report = compute_corpus_analysis(final_lines, hashtag_counter)
    
    text_report = f"""=====================================================
گزارش تحلیلی و آماری داده‌های متنی (Corpus Analyzer Report)
پروژه: amirmohammadshir1386-web/data-cleaning
=====================================================

آمار کمی پیکره:
- کل جملات معتبر نهایی: {report.total_lines}
- کل کلمات نهایی: {report.total_words}
- کل کاراکترهای نهایی: {report.total_characters}
- واژگان یکتا (Distinct Vocabulary): {report.unique_vocabulary_count}

میانگین‌ها:
- میانگین طول جملات: {report.avg_sentence_length} کلمه
- میانگین طول واژه‌ها: {report.avg_word_length} کاراکتر
- تعداد هشتگ‌های شناسایی‌شده: {len(report.hashtags_found)}

پربسامدترین کلمات:
"""
    for idx, item in enumerate(report.top_words[:20], start=1):
        text_report += f"{idx}. {item['word']}: {item['count']} مرتبه ({item['percentage']}%)\n"

    text_report += "\n=====================================================\n"

    return Response(
        content=text_report,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=analyzer.txt"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
