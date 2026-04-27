# explaintrust/feature_extraction.py

import nltk
import re
from nltk.stem.snowball import SnowballStemmer
from .linguistic_data import (
    DISCURSIVE_SINGLE, DOUBT_MARKERS, DOUBT_PHRASES,
    QUESTION_WORDS, LENGTH_THRESHOLD
)

# Инициализация русского стеммера (замена pymorphy2)
stemmer = SnowballStemmer('russian')


def compute_external_features(text: str) -> dict:
    sentences = nltk.sent_tokenize(text, language='russian')
    words = nltk.word_tokenize(text, language='russian')
    N_sent = len(sentences)
    N_words = len(words)

    # Структурная целостность SI
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    N_abz = len(paragraphs)
    si_abz = min(N_abz / max(N_sent, 1), 1.0)
    struct_pattern = r'(во-первых|во-вторых|в-третьих|в частности|' \
                     r'таким образом|следовательно|итак|наконец|' \
                     r'кроме того|более того)'
    struct_count = len(re.findall(struct_pattern, text.lower()))
    si_struct = struct_count / max(N_sent, 1)
    SI = (si_abz + si_struct) / 2.0

    # Маркеры связности CM
    N_disc = sum(1 for w in words if w.lower() in DISCURSIVE_SINGLE)
    CM = N_disc / max(N_words, 1)

    # Лексическое разнообразие LD (MATTR) с использованием стеммера
    # Стемминг вместо лемматизации
    stems = [stemmer.stem(w) for w in words if w.isalpha()]
    window = 10
    ttrs = []
    if len(stems) >= window:
        for i in range(len(stems) - window + 1):
            win = stems[i:i+window]
            ttrs.append(len(set(win)) / window)
        LD = sum(ttrs) / len(ttrs)
    else:
        LD = 0.0

    return {'SI': SI, 'CM': CM, 'LD': LD}


def compute_internal_features(text: str) -> dict:
    words = nltk.word_tokenize(text, language='russian')
    N_words = len(words)

    # Маркеры сомнения DM
    N_doubt = 0
    for w in words:
        if w.lower() in DOUBT_MARKERS:
            N_doubt += 1
    bigrams = [' '.join(words[i:i+2]).lower() for i in range(len(words)-1)]
    for bg in bigrams:
        if bg in DOUBT_PHRASES:
            N_doubt += 1
    DM = min(N_doubt / max(N_words, 1), 1.0)

    # Переспрос FQ
    has_question = '?' in text
    text_lower = text.lower().strip()
    starts_with_qw = any(text_lower.startswith(qw) for qw in QUESTION_WORDS)
    has_clarify = any(phrase in text_lower for phrase in
                      ['то есть', 'в смысле', 'уточни', 'поясни'])
    FQ = 1 if has_question and (starts_with_qw or has_clarify) else 0

    # Длина ответа RL
    RL = min(N_words / LENGTH_THRESHOLD, 1.0)

    return {'DM': DM, 'FQ': FQ, 'RL': RL}