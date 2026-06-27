import regex as re

# یه بار کامپایل میشه
DATE_PATTERN    = re.compile(r'"?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"?,?')
NUMBERS_PATTERN = re.compile(r'(?:,\d+)+\s*$')


def parse_csv(path: str):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            line = DATE_PATTERN.sub('', line)      # حذف تاریخ از اول
            line = NUMBERS_PATTERN.sub('', line)   # حذف همه اعداد از آخر یکجا
            line = line.strip().strip(',')

            if line:
                yield line


with open('extracted.csv', 'w', encoding='utf-8', errors='ignore') as out:
    for row in parse_csv('tweets.csv'):
        out.write(row + '\n')