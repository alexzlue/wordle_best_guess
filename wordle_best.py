from unittest import result
from words import SECRET_WORDS
from words import VALID_WORDS

import sys
from collections import Counter, defaultdict
from itertools import product
import multiprocessing as mp
from tqdm import tqdm
import time


# SECRET_WORDS are also VALID_WORDS
VALID_WORDS += SECRET_WORDS

# Weights
W_WGT = 0.0
Y_WGT = 0.02
G_WGT = 0.05

def get_hint(secret, guess, seq=True):
    '''Get wordle hint as tuple.
       ie: (0, 0, 1, 1, 2) -> White, White, Yellow, Yellow, Green
       if seq is false it only returns number of white, yellow, and green
    '''
    ylws = defaultdict(int)
    grns = defaultdict(int)
    sec_ctr = Counter(secret)
    hint = [-1] * 5
    for i, (g, s) in enumerate(zip(guess, secret)):
        if g == s:
            grns[g] += 1
            hint[i] = 2
    for i, (g, s) in enumerate(zip(guess, secret)):
        if hint[i] < 0 and g in sec_ctr and (ylws[g] + grns[g] < sec_ctr[g]):
            ylws[g] += 1
            hint[i] = 1
    hint = [i if i>0 else 0 for i in hint]
    if not seq:
        return Counter(hint)
    return tuple(hint)


def print_results(guess_scores, result_type='Best'):
    print('Top {} {} 1st Guess Words:'.format(len(guess_scores), result_type))
    for i, (word, score) in enumerate(guess_scores):
        print('{}. {}\t{}'.format(i+1, word, round(score, 2)))


def best_weighted_guess():
    '''Get top 10 wordle words based off arbitrary weighting.'''
    print('testing valid words ({}) with secret words ({})'.format(len(VALID_WORDS), len(SECRET_WORDS)))
    total_combos = len(SECRET_WORDS) * len(VALID_WORDS)
    print('total combinations: {}'.format(total_combos))

    guess_scores = defaultdict(float)
    for guess, secret in tqdm(product(VALID_WORDS, SECRET_WORDS), total=total_combos):
        hint = get_hint(secret, guess, seq=False)
        guess_scores[guess] += hint[0]*W_WGT + hint[1]*Y_WGT + hint[2]*G_WGT
    guess_scores_ctr = Counter(guess_scores).most_common(10)
    print_results(guess_scores_ctr)



def reduce_wordspace(guess, hint):
    '''
    if space is green -> get all words with the same letter
    if space is white -> remove all words with these letters. if there is a yellow or green of the same letter preceding, then the word is ok.
    if space is yellow -> remove all words with that letter in that position but still in word
    '''
    counts = 0
    for word in VALID_WORDS:
        valid_w = True
        for i, (w, g, h) in enumerate(zip(word, guess, hint)):
            g_in_word = g in word
            # check green
            if h == 2:
                ok = (w == g)
            # check yellow
            if h == 1:
                ok = (w != g) and (g_in_word)
            # check white
            if h == 0:
                if g_in_word:
                    sub_word = guess[:i]
                    ok = g in sub_word and hint[sub_word.index(g)] in (1, 2)
                else:
                    ok = True
            if not ok:
                valid_w = False
                break
        if valid_w:
            counts += 1
    return counts


def write_to_csv(file_name, guess_scores):
    with open(file_name, 'w') as fp:
        fp.write('word,wordspace\n')
        for guess, score in guess_scores:
            fp.write('{},{}\n'.format(guess, score))

manager = mp.Manager()
wordspaces = manager.dict()


def process_words(valid_words):
    global wordspaces
    for guess in valid_words:
        agg_wordspace = 0
        for secret in SECRET_WORDS:
            hint = get_hint(secret, guess)
            agg_wordspace += reduce_wordspace(guess, hint)
        avg_wordspace = agg_wordspace / len(SECRET_WORDS)
        wordspaces[guess] = avg_wordspace
    if len(wordspaces) % 1000000 == 0:
        print(len(wordspaces))


def best_reduced_wordspace():
    '''Get top 10 wordle words based off resulting word groups.'''
    print('testing {} valid words with {} secret words'.format(len(VALID_WORDS), len(SECRET_WORDS)))
    num_secrets = len(SECRET_WORDS)
    total_combos = len(VALID_WORDS) * num_secrets
    print('total combinations: {}'.format(total_combos))
    processes = []
    cpus = mp.cpu_count()
    num_per_process = len(VALID_WORDS) // cpus
    for i in range(cpus):
        valid_words = VALID_WORDS[(i*num_per_process):((i+1)*num_per_process)]
        if i == cpus - 1:
            valid_words = VALID_WORDS[(i*num_per_process):]
        processes.append(mp.Process(target=process_words, args=([valid_words])))
    s = time.time()
    for process in processes:
        process.start()
    for process in processes:
        process.join()
    e = time.time()
    h = int((e - s) // 3600)
    m = int((e - s - (h * 3600)) // 60)
    sec = (e - s - (h * 3600) - (m * 60))
    print('Total Processing time: {}h {}m {}s'.format(h, m, round(sec, 2)))

    global wordspaces
    guess_scores = {word: avg_ws for word, avg_ws in wordspaces.items()}
    guess_scores = Counter(guess_scores).most_common()
    write_to_csv('best_first_guess_words.csv', guess_scores[::-1])
    print_results(guess_scores[-10:][::-1])
    print_results(guess_scores[:10], 'Worst')


if __name__ == "__main__":
    best_reduced_wordspace()
    # best_weighted_guess()
