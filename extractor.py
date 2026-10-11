import csv
import regex as re

DATE_PATTERN = re.compile(r'"?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"?,?')
NUMERIC_FIELD_PATTERN = re.compile(r'^-?[\d۰-۹]+(?:[.,][\d۰-۹]+)?$')


def parse_csv(path: str):
    with open(path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
        reader = csv.reader(f)

        for i, row in enumerate(reader):
            if not row:
                continue

            if i == 0 and row[0].strip().lower() == 'text':
                continue

            while row and NUMERIC_FIELD_PATTERN.fullmatch(row[-1].strip()):
                row.pop()

            if not row:
                continue

            text = ','.join(row).strip()
            text = DATE_PATTERN.sub('', text)
            text = text.strip().strip(',').strip()

            if text:
                yield text


def runner(data_path: str | None = None) -> None:
    if data_path is None:
        data_path = input("Please enter the raw data name:\n")

    print("⏳ Extracting raw data...")

    with open('output files/extracted.csv', 'w', encoding='utf-8', errors='ignore') as out:
        for row in parse_csv(data_path):
            out.write(row + '\n')
