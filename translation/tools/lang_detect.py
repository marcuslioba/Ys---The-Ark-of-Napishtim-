import re

STOPWORDS = {
    'en': {'the', 'you', 'your', 'and', 'is', 'to', 'of', 'a', 'it', 'that',
           'this', 'have', 'with', 'for', 'was', 'are', 'my', 'me', 'i',
           'he', 'she', 'we', 'they', 'what', 'not', 'but', 'on', 'be',
           "don't", "i'm", "it's", "you're", "that's"},
    'fr': {'le', 'la', 'les', 'de', 'et', 'vous', 'je', 'que', 'un', 'une',
           'des', 'est', 'pas', 'pour', 'avec', 'ne', 'se', 'qui', 'au',
           'dans', 'ce', 'il', 'elle', 'nous'},
    'de': {'der', 'die', 'das', 'und', 'ich', 'ist', 'nicht', 'ein', 'eine',
           'sie', 'es', 'zu', 'mit', 'den', 'dem', 'du', 'wir', 'auf', 'sich',
           'war', 'wie', 'aber'},
    'es': {'el', 'la', 'los', 'las', 'de', 'que', 'y', 'usted', 'es', 'un',
           'una', 'no', 'para', 'con', 'se', 'lo', 'te', 'yo', 'mi', 'tu',
           'esto', 'pero'},
    'it': {'il', 'la', 'di', 'che', 'e', 'un', 'una', 'non', 'per', 'con',
           'si', 'lei', 'io', 'mi', 'ti', 'ma', 'gli', 'sono', 'questo'},
}


TAG_RE = re.compile(r'<[^>]*>')
NAME_RE = re.compile(r'\b(Adol|Olha|Isha|Dogi|Geis|Terra|Raba|Ord|Ur|Baslam|Quval|Cloa|'
                      r'Emilio|Ernst|Rothaar|Rakche|Ryug|Romun|Rehda|Eresian[s]?|Alma|'
                      r'Camara|Quatera|Zemeth)\b')


def detect(text: str):
    cleaned = TAG_RE.sub(' ', text)
    cleaned = NAME_RE.sub(' ', cleaned)
    words = re.findall(r"[a-zA-ZÀ-ÿ']+", cleaned.lower())
    if not words:
        return 'punct'
    scores = {lang: 0 for lang in STOPWORDS}
    for w in words:
        for lang, sw in STOPWORDS.items():
            if w in sw:
                scores[lang] += 1
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    best, best_score = ranked[0]
    second_score = ranked[1][1]
    if any(ord(c) > 127 for c in cleaned):
        has_accents = True
    else:
        has_accents = False
    if best_score == 0:
        return 'accented_unknown' if has_accents else 'ascii_unknown'
    # require a clear margin over the runner-up, and at least 2 hits for short lines
    if best_score < 2 and len(words) > 3:
        return 'accented_unknown' if has_accents else 'ascii_unknown'
    if second_score > 0 and best_score <= second_score:
        return 'ambiguous'
    if best == 'en' and has_accents:
        return 'ambiguous'  # English never carries accented letters in this game
    return best
