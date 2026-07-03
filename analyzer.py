import sys

# ── مسیرها ───────────────────────────────────────────────────────────────────
OUTPUT_DIR = 'output files'
FINAL_PATH = f'{OUTPUT_DIR}/final.csv'
REPORT_PATH = 'analyzer.txt'
CHUNK_SIZE = 10000


def _iter_chunks(path: str, chunk_size: int):
    """
    final.csv را خط‌به‌خط و به‌صورت قطعه‌قطعه (chunk) می‌خواند —
    نه با pd.read_csv، چون final.csv یک CSV واقعی نیست (صرفاً یک جمله
    در هر خط) و اگر خودِ متن یک جمله هم کاما داشته باشد، pd.read_csv
    آن را delimiter در نظر می‌گیرد و خطای پارس می‌دهد.
    """
    chunk = []
    with open(path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            chunk.append(line)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
    if chunk:
        yield chunk


def analyzer():
    """
    طول جملات فایل نهایی (final.csv) را بررسی می‌کند و کوتاه‌ترین و بلندترین
    جمله را (بر اساس تعداد کاراکتر) در analyzer.txt ثبت می‌کند.

    نکته: هر خط از final.csv از قبل توسط SentenceTokenizer در فاز ۴ main.py
    به یک جمله‌ی مجزا شکسته شده، پس نیازی به توکنایز دوباره نیست —
    هر خط مستقیماً به‌عنوان یک جمله در نظر گرفته می‌شود.
    """
    max_len = 0
    max_sent = ''
    min_len = sys.maxsize
    min_sent = ''
    total_count = 0

    for chunk in _iter_chunks(FINAL_PATH, CHUNK_SIZE):
        for sentence in chunk:
            length = len(sentence)
            total_count += 1

            # این دو شرط باید مستقل باشن نه elif، وگرنه اولین جمله
            # (که همیشه بزرگ‌ترینِ دیده‌شده تا اون لحظه‌ست) هیچ‌وقت
            # به‌عنوان کاندید کوچک‌ترین بررسی نمی‌شه
            if length > max_len:
                max_len = length
                max_sent = sentence

            if length < min_len:
                min_len = length
                min_sent = sentence

    with open(REPORT_PATH, 'a', encoding='utf-8') as f:
        print("── تحلیل طول جملات ──────────────────", file=f)
        if total_count == 0:
            print("⚠️ هیچ جمله‌ای برای تحلیل پیدا نشد.", file=f)
            return
        print(f"تعداد کل جملات بررسی‌شده: {total_count:,}", file=f)
        print(f"بزرگ‌ترین طول جمله: {max_len} کاراکتر — نمونه: {max_sent}", file=f)
        print(f"کوچک‌ترین طول جمله: {min_len} کاراکتر — نمونه: {min_sent}", file=f)


if __name__ == '__main__':
    analyzer()
