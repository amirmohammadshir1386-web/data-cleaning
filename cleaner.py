import os
import regex as re
from collections import Counter
import hazm as hz
from huggingface_hub import hf_hub_download


# ──────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

# ──────────────────────────────────────────────
# Model loading
# ──────────────────────────────────────────────
model_path = hf_hub_download(
    repo_id="roshan-research/hazm-postagger",
    filename="pos_tagger.model",
    cache_dir="./hf_cache"
)

# ──────────────────────────────────────────────
# Hazm instances (یه بار ساخته میشن)
# ──────────────────────────────────────────────
normalizer         = hz.Normalizer(decrease_repeated_chars=False)
informal_normalizer = hz.InformalNormalizer()
tokenizer          = hz.WordTokenizer()
tagger             = hz.POSTagger(model=model_path)

# ──────────────────────────────────────────────
# Compiled patterns (یه بار کامپایل میشن)
# ──────────────────────────────────────────────
HASHTAG_PATTERN       = re.compile(r'#[\u0600-\u06FF\d_]+')
MENTION_PATTERN       = re.compile(r'@[A-Za-z0-9_]+')
HTTP_PATTERN          = re.compile(r'https?://[^ ]+')
WWW_PATTERN           = re.compile(r'www\.[^ ]+')
NON_PERSIAN_PATTERN   = re.compile(r'[^\u0600-\u06FF\s]')
REPEATED_CHAR_PATTERN = re.compile(r'([^\p{L}\p{N}\s])\1+')
REPEATED_PERSIAN_PATTERN = re.compile(r'([ا-ی])\1+')
WHITESPACE_PATTERN    = re.compile(r'\s+')
NOISE_NUMBER_PATTERN  = re.compile(r'\b[\d۰-۹]{7,}\b')
NUMBER_PATTERN        = re.compile(r'[\d۰-۹]+')
PREV_WORD_PATTERN     = re.compile(r'([\p{L}]+)\s*$')
NEXT_WORD_PATTERN     = re.compile(r'\s*([\p{L}%٪]+)')
EMOJI_PATTERN         = re.compile(r'\p{Emoji}')

# ──────────────────────────────────────────────
# اعداد معنادار
# ──────────────────────────────────────────────
VALUABLE_BEFORE = frozenset({
    'سال', 'ماه', 'روز', 'ماده', 'بند', 'صفحه', 'شماره',
})

VALUABLE_AFTER = frozenset({
    'سال', 'ساله', 'ماه', 'ماهه', 'روز', 'روزه',
    'درصد', 'درصدی', '%', '٪',
    'تومان', 'ریال', 'میلیون', 'میلیارد', 'هزار',
    'شاخص', 'نفر', 'بار',
    'کیلو', 'کیلومتر', 'متر', 'سانتی',
    'دلار', 'یورو',
})


# ──────────────────────────────────────────────
# توابع پاکسازی کمکی
# ──────────────────────────────────────────────


def count_hashtags(tweets_iterator) -> set[str]:
    hashtag_counter = Counter()

    for tweet in tweets_iterator:
        hashtag_counter.update(HASHTAG_PATTERN.findall(tweet))

    return {
        tag for tag, count in hashtag_counter.items()
        if 10 <= count <= 500_000
    }


def clean_hashtag_by_freq(tweet: str, valid_hashtags: set[str]) -> str:
    for tag in HASHTAG_PATTERN.findall(tweet):
        if tag not in valid_hashtags:
            tweet = tweet.replace(tag, '')
        else:
            word_inside = tag[1:].replace('_', ' ')  # حذف # با slice
            tweet = tweet.replace(tag, word_inside)
    return tweet


def clean_url(tweet: str) -> str:
    tweet = MENTION_PATTERN.sub('', tweet)
    tweet = HTTP_PATTERN.sub('', tweet)
    tweet = WWW_PATTERN.sub('', tweet)
    return tweet


def clean_hashtag(tweet: str) -> str:
    return HASHTAG_PATTERN.sub('', tweet)


def clean_number(tweet: str) -> str:
    tweet = NOISE_NUMBER_PATTERN.sub('', tweet)

    def replacer(match: re.Match) -> str:
        start, end = match.span()
        prev_match = PREV_WORD_PATTERN.search(tweet[:start])
        next_match = NEXT_WORD_PATTERN.match(tweet[end:])

        if (prev_match and prev_match.group(1) in VALUABLE_BEFORE) or \
           (next_match and next_match.group(1) in VALUABLE_AFTER):
            return match.group()
        return ''

    tweet = NUMBER_PATTERN.sub(replacer, tweet)
    return WHITESPACE_PATTERN.sub(' ', tweet).strip()


def clean_all_without_persian(tweet: str) -> str:
    return NON_PERSIAN_PATTERN.sub('', tweet)


def clean_repeated_emojis(tweet: str) -> str:
    return REPEATED_CHAR_PATTERN.sub('', tweet)


def clean_repeated_persian(tweet: str) -> str:
    PERSIAN_DOUBLE_EXCEPTIONS = frozenset({'شش', 'کک'})
    def replacer(m: re.Match) -> str:
        seq = m.group()
        if seq in PERSIAN_DOUBLE_EXCEPTIONS:
            return seq
        return m.group(1)
    return REPEATED_PERSIAN_PATTERN.sub(replacer, tweet)


# ──────────────────────────────────────────────
# تابع اصلی
# ──────────────────────────────────────────────

def is_sen(tweet: list[str], valid_hashtags: set[str]) -> tuple[bool, str]:
    tweet = ''.join(tweet)
    tweet = clean_url(tweet)
    tweet = clean_hashtag_by_freq(tweet, valid_hashtags)
    tweet = clean_number(tweet)
    tweet = clean_repeated_emojis(tweet)
    tweet = normalizer.normalize(tweet)
    tweet = clean_repeated_persian(tweet)

    tokens = tokenizer.tokenize(tweet)
    tags   = tagger.tag(tokens)

    has_verb = (any(tag == 'VERB' for _, tag in tags) and len(tokens) >= 3)

    return has_verb, tweet