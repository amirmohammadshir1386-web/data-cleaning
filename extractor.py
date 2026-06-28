import regex as re

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
def runer(data_path = input("لطفا نام دیتا خام را وارد کنید:\n")):
    print("در حال استخراج داده های خام")
    with open('output files/extracted.csv', 'w', encoding='utf-8', errors='ignore') as out:
        for row in parse_csv(data_path):
            out.write(row + '\n')
