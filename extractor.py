import csv
import regex as re

DATE_PATTERN = re.compile(r'"?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"?,?')
NUMERIC_FIELD_PATTERN = re.compile(r'^-?[\d۰-۹]+(?:[.,][\d۰-۹]+)?$')


def parse_csv(path: str):
    """
    فایل CSV خام را با ماژول استاندارد csv می‌خواند، نه خط‌به‌خط ساده.

    دلیل: بعضی رکوردها متن‌شون داخل quote یه newline واقعی دارن (یعنی یک
    توییت می‌تونه چند خط فیزیکی رو اشغال کنه). خواندن ساده‌ی `for line in f`
    این‌جور رکوردها رو از وسط می‌شکنه و کل فایل رو خراب می‌کنه. csv.reader
    این حالت رو استاندارد و درست مدیریت می‌کنه.
    """
    with open(path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.reader(f)

        for i, row in enumerate(reader):
            if not row:
                continue

            # ردیف هدر رو رد کن (فقط اگه واقعاً ردیف اوله و اسم ستون اوله «text»ه)
            if i == 0 and row[0].strip().lower() == 'text':
                continue

            # حذف ستون‌های عددی انتهایی (امتیاز احساسات، لایک، ریتوییت و ...)
            # به هر تعدادی که باشن — رویکرد column-agnostic، مثل قبل
            while row and NUMERIC_FIELD_PATTERN.fullmatch(row[-1].strip()):
                row.pop()

            if not row:
                continue

            # اگه بعد از حذف ستون‌های عددی هنوز چند فیلد مونده (مثلاً تاریخ + متن)،
            # با کاما به هم می‌چسبونیمشون تا همون منطق قبلی DATE_PATTERN روش کار کنه
            text = ','.join(row).strip()
            text = DATE_PATTERN.sub('', text)  # حذف تاریخ از اول (اگه بود)
            text = text.strip().strip(',').strip()

            if text:
                yield text


def runner(data_path: str | None = None) -> None:
    if data_path is None:
        data_path = input("لطفا نام دیتای خام را وارد کنید:\n")

    print("⏳ در حال استخراج داده‌های خام...")

    with open('output files/extracted.csv', 'w', encoding='utf-8', errors='ignore') as out:
        for row in parse_csv(data_path):
            out.write(row + '\n')
