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

COMMA_SPLIT_PATTERN = re.compile(r'[،,]')

# ── Routes ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = 'output files'
EXTRACTED_PATH = f'{OUTPUT_DIR}/extracted.csv'
UNIQUE_PATH = f'{OUTPUT_DIR}/unique.csv'
FINAL_PATH = f'{OUTPUT_DIR}/final.csv'
REPORT_PATH = 'analyzer.txt'

# Ensure the output folder exists.
os.makedirs(OUTPUT_DIR, exist_ok=True)


def log(message: str) -> None:
    print(message)
    with open(REPORT_PATH, 'a', encoding='utf-8') as f:
        print(message, file=f)


def extract_sentences(tweets_iterator):
    for tweet in tweets_iterator:
        for sent in sentence_tokenizer.tokenize(tweet):
            for piece in COMMA_SPLIT_PATTERN.split(sent):
                piece = piece.strip()
                if piece:
                    yield piece


def remove_duplicates(input_path: str, output_path: str) -> None:
    print("⏳ Phase 2: Removing duplicates...")
    with open(input_path, encoding='utf-8', errors='ignore') as f:
        lines = [line.rstrip('\n') for line in f if line.strip()]

    df = pd.DataFrame({'text': lines})
    df_unique = df.drop_duplicates(subset=['text'])
    log(f"   Total: {len(df):,}  |  Unique: {len(df_unique):,}")

    with open(output_path, 'w', encoding='utf-8') as out:
        for text in df_unique['text']:
            out.write(text + '\n')


def iter_lines(path: str):
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


if __name__ == '__main__':

    open(REPORT_PATH, 'w', encoding='utf-8').close()
    
    # ── Phase 1: Extraction ───────────────────────────────────────────────────────
    ex.runner()
    log("✅ Phase 1: Extraction completed.")
    
    # ── Phase 2: Removing duplicates ──────────────────────────────────────────────
    remove_duplicates(EXTRACTED_PATH, UNIQUE_PATH)
    log("✅ Phase 2: Removal of duplicates completed.")
    
    # ── Phase 3: Counting Hashtags — First Pass Over the File ─────────────────────
    print("⏳ فاز ۳: شمارش هشتگ‌ها...")
    valid_hashtags = cl.count_hashtags(iter_lines(UNIQUE_PATH))
    log(f"✅ Phase 3: {len(valid_hashtags):,} A valid hashtag was found.")
    
    # ── Phase 4: Parallel Cleanup — Second Pass Over the File ─────────────────────
    print("⏳ Phase 4: Cleaning up tweets...")
    worker = partial(cl.is_sen, valid_hashtags=valid_hashtags)
    count = 0

    with open(FINAL_PATH, 'w', encoding='utf-8') as out:
        with Pool() as pool:
            for ok, clean in pool.imap(worker, extract_sentences(iter_lines(UNIQUE_PATH)), chunksize=200):
                if ok:
                    out.write(clean + '\n')
                    count += 1

    log(f"✅ Phase 4: {count:,} Credible tweet → {FINAL_PATH}")

    # ── Phase 5: Sentence Length Analysis ─────────────────────────────────────────
    print("⏳ Phase 5: Sentence length analysis...")
    ac.analyzer()
    log("✅ Phase 5: Sentence length analysis completed.")