import cleaner

def parse_csv(path: str):
    with open(path, 'r', encoding='utf-8', errors='ignore') as csv:
        for row in csv:
            yield row.strip().split(',')