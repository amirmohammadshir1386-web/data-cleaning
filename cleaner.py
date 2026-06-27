import os
import regex as re
from collections import Counter
import hazm as hz
from huggingface_hub import hf_hub_download

os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

model_path = hf_hub_download(
    repo_id="roshan-research/hazm-postagger",
    filename="pos_tagger.model",
    cache_dir="./hf_cache"
)

normalizer = hz.Normalizer()
informal_normalizer = hz.InformalNormalizer()
tokenizer = hz.WordTokenizer()
tagger = hz.POSTagger(model=model_path)


def has_emoji(text: str) -> bool:
    return bool(re.search(r'\p{Emoji}', text))


def count_hashtags(tweets_iterator) -> set[str]:
    hashtag_pattern = re.compile(r'#[\u0600-\u06FF\d_]+')
    hashtag_counter = Counter()

    for tweet in tweets_iterator:
        hashtags = hashtag_pattern.findall(tweet)
        hashtag_counter.update(hashtags)

    min_freq = 10
    max_freq = 500000

    valid_hashtags = {
        tag for tag, count in hashtag_counter.items()
        if min_freq <= count <= max_freq
    }

    return valid_hashtags


def clean_hashtag_by_freq(tweet: str, valid_hashtags: set[str]) -> str:
    hashtag_pattern = re.compile(r'#[\u0600-\u06FF\d_]+')
    current_hashtags = hashtag_pattern.findall(tweet)

    for tag in current_hashtags:
        if tag not in valid_hashtags:
            tweet = tweet.replace(tag, '')
        else:
            word_inside = tag.replace('#', '').replace('_', ' ')
            tweet = tweet.replace(tag, word_inside)

    return tweet


def is_sen(tweet: list[str], valid_hashtags: set[str]):
    tweet = ''.join(tweet)
    tweet = clean_url(tweet)
    tweet = clean_hashtag_by_freq(tweet, valid_hashtags)
    tweet = clean_number(tweet)
    tweet = clean_repeated_emojis(tweet)
    tweet = normalization(tweet)

    tokens = tokenizer.tokenize(tweet)
    tags = tagger.tag(tokens)

    has_verb = (
        any(tag == 'VERB' for word, tag in tags) and len(tokens) >= 3
    ) or (
        len(tokens) >= 1 and has_emoji(tweet)
    )

    return has_verb, tweet


def clean_url(tweet: str) -> str:
    tweet = re.sub(r'@[A-Za-z0-9_]+', '', tweet)
    tweet = re.sub(r'https?://[^ ]+', '', tweet)
    tweet = re.sub(r'www\.[^ ]+', '', tweet)
    return tweet


def clean_hashtag(tweet: str) -> str:
    tweet = re.sub(r'#\w+', '', tweet)
    return tweet


def clean_number(tweet: str) -> str:
    noise_numbers_pattern = re.compile(r'\b[\d۰-۹]{7,11}\b')
    tweet = re.sub(noise_numbers_pattern, '', tweet)

    valuable_complement_pattern = re.compile(
        r'[\d۰-۹]+(?!\s*(?:٪|%|تومان|ریال|سال|میلیون|هزار|درصد|درصدی|شاخص|میلیارد))'
    )
    tweet = re.sub(valuable_complement_pattern, '', tweet)
    return tweet


def clean_all_without_persian(tweet: str) -> str:
    tweet = re.sub(r'[^\u0600-\u06FF\s]', '', tweet)
    return tweet


def clean_repeated_emojis(tweet: str) -> str:
    repeated_emoji_pattern = re.compile(r'([^\p{L}\p{N}\s])\1+')
    tweet = re.sub(repeated_emoji_pattern, r'\1', tweet)
    return tweet


def normalization(tweet: str) -> str:
    tweet = informal_normalizer.normalize(tweet)
    tweet = normalizer.normalize(tweet)
    return tweet