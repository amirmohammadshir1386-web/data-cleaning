import os
import pandas as pd
from multiprocessing import Pool
from functools import partial
import extractor as ex
import cleaner as cl
from hazm import SentenceTokenizer

sentence_tokenizer = SentenceTokenizer()

# ── مسیرها ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = 'output files'
EXTRACTED_PATH = f'{OUTPUT_DIR}/extracted.csv'
UNIQUE_PATH = f'{OUTPUT_DIR}/unique.csv'
FINAL_PATH = f'{OUTPUT_DIR}/final.csv'

# اطمینان از وجود پوشه خروجی
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_sentences(tweets_iterator):
    """جملات را با استفاده از Hazm توکنایز می‌کند."""
    for tweet in tweets_iterator:
        for sent in sentence_tokenizer.tokenize(tweet):
            yield sent


def remove_duplicates(input_path: str, output_path: str) -> None:
    print("⏳ فاز ۲: حذف تکراری‌ها...")
    df = pd.read_csv(input_path, names=['text'], header=None)
    df_unique = df.drop_duplicates(subset=['text'])
    print(f"   کل: {len(df):,}  |  یکتا: {len(df_unique):,}")
    df_unique.to_csv(output_path, index=False, header=False, encoding='utf-8')


def iter_lines(path: str):
    """سطر به سطر می‌خونه — کل فایل رو توی رم نمی‌ریزه."""
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


if __name__ == '__main__':

    # ── فاز ۱: استخراج ───────────────────────────────────────────────────────
    ex.runner()
    print("✅ فاز ۱: استخراج پایان یافت.")

    # ── فاز ۲: حذف تکراری‌ها ─────────────────────────────────────────────────
    remove_duplicates(EXTRACTED_PATH, UNIQUE_PATH)
    print("✅ فاز ۲: حذف تکراری‌ها پایان یافت.")

    # ── فاز ۳: شمارش هشتگ‌ها — پاس اول روی فایل ─────────────────────────────
    print("⏳ فاز ۳: شمارش هشتگ‌ها...")
    valid_hashtags = cl.count_hashtags(iter_lines(UNIQUE_PATH))
    print(f"✅ فاز ۳: {len(valid_hashtags):,} هشتگ معتبر پیدا شد.")

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

    print(f"✅ فاز ۴: {count:,} توییت معتبر → {FINAL_PATH}")

    # نکته برای گزارش: برای استخراج طول جملات (بخش تحلیل طول جملات در داکیومنت)
    # می‌توانی بعد از پایان این فاز، فایل final.csv را باز کرده و طول را محاسبه کنی.