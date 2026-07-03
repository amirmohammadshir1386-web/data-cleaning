import os
import re
import pandas as pd
from multiprocessing import Pool
from functools import partial
import extractor as ex
import cleaner as cl
from hazm import SentenceTokenizer
import analyzer as ac

sentence_tokenizer = SentenceTokenizer()

# SentenceTokenizer هزم فقط روی نقطه/تعجب/سؤال می‌شکنه، نه ویرگول.
# در نتیجه توییت‌هایی که لیستی از کلمات با ویرگول جدا شده‌ن (نه جمله‌ی واقعی)
# به‌عنوان یک «جمله»‌ی خیلی بلند و بی‌معنا وارد فاز ۴ می‌شدن و چون معمولاً
# جایی وسطشون یه فعل (درست یا اشتباه‌تگ‌خورده) پیدا می‌شد، رد می‌شدن.
COMMA_SPLIT_PATTERN = re.compile(r'[،,]')

# ── مسیرها ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = 'output files'
EXTRACTED_PATH = f'{OUTPUT_DIR}/extracted.csv'
UNIQUE_PATH = f'{OUTPUT_DIR}/unique.csv'
FINAL_PATH = f'{OUTPUT_DIR}/final.csv'
REPORT_PATH = 'analyzer.txt'

# اطمینان از وجود پوشه خروجی
os.makedirs(OUTPUT_DIR, exist_ok=True)


def log(message: str) -> None:
    """
    پیام را هم توی کنسول چاپ می‌کنه هم توی analyzer.txt ذخیره می‌کنه.
    این تابع جای print(..., file=f) پراکنده رو می‌گیره تا دیگه جایی
    فراموش نشه که file=f رو پاس بدیم.
    """
    print(message)
    with open(REPORT_PATH, 'a', encoding='utf-8') as f:
        print(message, file=f)


def extract_sentences(tweets_iterator):
    """
    جملات را با استفاده از Hazm توکنایز می‌کند و سپس هر جمله را
    روی ویرگول (، یا ,) هم می‌شکند تا لیست‌های کلمات ویرگول‌دار
    به‌عنوان یک جمله‌ی واحد و بیش‌ازحد بلند وارد فاز پاکسازی نشوند.
    """
    for tweet in tweets_iterator:
        for sent in sentence_tokenizer.tokenize(tweet):
            for piece in COMMA_SPLIT_PATTERN.split(sent):
                piece = piece.strip()
                if piece:
                    yield piece


def remove_duplicates(input_path: str, output_path: str) -> None:
    """
    extracted.csv یک فایل CSV واقعی نیست — صرفاً یک فایل متنیه که هر خطش
    یک توییته و ممکنه خودِ متن هر خط شامل کاما (، یا ,) هم باشه. پس نباید
    با pd.read_csv خوندش (چون کاما رو delimiter می‌بینه و اگه متن خودش
    کاما داشته باشه، خطای «Expected 1 fields, saw 2» می‌ده). به‌جاش خط‌به‌خط
    می‌خونیم، دقیقاً هم‌روش با iter_lines.
    """
    print("⏳ فاز ۲: حذف تکراری‌ها...")
    with open(input_path, encoding='utf-8', errors='ignore') as f:
        lines = [line.rstrip('\n') for line in f if line.strip()]

    df = pd.DataFrame({'text': lines})
    df_unique = df.drop_duplicates(subset=['text'])
    log(f"   کل: {len(df):,}  |  یکتا: {len(df_unique):,}")

    # اینجا هم به همون دلیل، از to_csv عادی استفاده نمی‌کنیم چون pandas
    # به‌صورت خودکار متن‌های حاوی کاما رو quote می‌کنه و باز فایل خروجی
    # واقعی CSV می‌شه؛ در عوض مستقیم خط‌به‌خط می‌نویسیم.
    with open(output_path, 'w', encoding='utf-8') as out:
        for text in df_unique['text']:
            out.write(text + '\n')


def iter_lines(path: str):
    """سطر به سطر می‌خونه — کل فایل رو توی رم نمی‌ریزه."""
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


if __name__ == '__main__':

    # ریست کردن فایل گزارش در ابتدای هر اجرا — تا گزارش‌های اجرای قبلی
    # با اجرای جدید قاطی نشن
    open(REPORT_PATH, 'w', encoding='utf-8').close()

    # ── فاز ۱: استخراج ───────────────────────────────────────────────────────
    ex.runner()
    log("✅ فاز ۱: استخراج پایان یافت.")

    # ── فاز ۲: حذف تکراری‌ها ─────────────────────────────────────────────────
    remove_duplicates(EXTRACTED_PATH, UNIQUE_PATH)
    log("✅ فاز ۲: حذف تکراری‌ها پایان یافت.")

    # ── فاز ۳: شمارش هشتگ‌ها — پاس اول روی فایل ─────────────────────────────
    print("⏳ فاز ۳: شمارش هشتگ‌ها...")
    valid_hashtags = cl.count_hashtags(iter_lines(UNIQUE_PATH))
    log(f"✅ فاز ۳: {len(valid_hashtags):,} هشتگ معتبر پیدا شد.")

    # ── فاز ۴: پاکسازی موازی — پاس دوم روی فایل ─────────────────────────────
    print("⏳ فاز ۴: پاکسازی توییت‌ها...")
    worker = partial(cl.is_sen, valid_hashtags=valid_hashtags)
    count = 0

    with open(FINAL_PATH, 'w', encoding='utf-8') as out:
        with Pool() as pool:
            # استفاده از نام جدید تابع extract_sentences
            for ok, clean in pool.imap(worker, extract_sentences(iter_lines(UNIQUE_PATH)), chunksize=200):
                if ok:
                    out.write(clean + '\n')
                    count += 1

    log(f"✅ فاز ۴: {count:,} توییت معتبر → {FINAL_PATH}")

    # ── فاز ۵: تحلیل طول جملات ───────────────────────────────────────────────
    print("⏳ فاز ۵: تحلیل طول جملات...")
    ac.analyzer()
    log("✅ فاز ۵: تحلیل طول جملات پایان یافت.")
