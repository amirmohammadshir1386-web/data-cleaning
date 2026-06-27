import regex as re
def parse_csv(path: str):
    with open(path, 'r', encoding='utf-8', errors='ignore') as csv:
        for line in csv:
            line = line.strip()
            line = re.sub(r'\"\d+-\d+-\d+ \d+:\d+:\d+\",', '', line)
            line = re.sub(r',\d+,', '', line)
            yield line

with open('extracted.csv', 'w', encoding='utf-8', errors='ignore') as csv:
    for row in parse_csv("tweets.csv"):
        row = ''.join(row)
        csv.write(row)