import sys

OUTPUT_DIR = 'output files'
FINAL_PATH = f'{OUTPUT_DIR}/final.csv'
REPORT_PATH = 'analyzer.txt'
CHUNK_SIZE = 10000


def _iter_chunks(path: str, chunk_size: int):
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
    max_len = 0
    max_sent = ''
    min_len = sys.maxsize
    min_sent = ''
    total_count = 0

    for chunk in _iter_chunks(FINAL_PATH, CHUNK_SIZE):
        for sentence in chunk:
            length = len(sentence)
            total_count += 1

            if length > max_len:
                max_len = length
                max_sent = sentence

            if length < min_len:
                min_len = length
                min_sent = sentence

    with open(REPORT_PATH, 'a', encoding='utf-8') as f:
        print("── Sentence Length Analysis ──────────────────", file=f)
        if total_count == 0:
            print("⚠️ No sentence was found for analysis.", file=f)
            return
        print(f"Total number of sentences examined: {total_count:,}", file=f)
        print(f"Maximum sentence length: {max_len} Character — Example: {max_sent}", file=f)
        print(f"Shortest sentence length: {min_len} Character — Example: {min_sent}", file=f)


if __name__ == '__main__':
    analyzer()
