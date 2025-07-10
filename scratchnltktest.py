import nltk
import re
import heapq
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

def clean(text):
    cleaned_text=re.sub(r'\s+', ' ', text) #looks for white space and scrubs it
    cleaned_text=re.sub(r'\[[0-9]*\]', ' ', cleaned_text) #looks for numerals and cleans them

    return cleaned_text

def makesometokens(text):
    # sentences = sent_tokenize(text)

    rough_sentences = re.split(r'[;,\.]', text)
    sentences = [s.strip() for s in rough_sentences if len(s.strip()) > 10]
    words = word_tokenize(text.lower())

    return sentences, words

def buildfreqtable(words):
    stop_words=set(stopwords.words("english"))
    freq_table = {}

    pos_tags = nltk.pos_tag(words)

    for word, pos in pos_tags:
        if word in stop_words:
            continue
        if pos.startswith("N"):
            weight = 1.5
        elif pos.startswith("V"):
            weight = 1.3
        else:
            weight = 1

        freq_table[word]=freq_table.get(word,0)+weight

    return freq_table

def setscores(text, freq_table):
    sentence_scores = {}

    for sentence in text:
        word_count = 0
        for word in word_tokenize(sentence.lower()):
            if word in freq_table:
                sentence_scores[sentence] = sentence_scores.get(sentence, 0) + freq_table[word]
                word_count+=1
        if sentence in sentence_scores and word_count > 0:
            sentence_scores[sentence] /= word_count

    return sentence_scores

def getsummary(sentence_scores, orig_sentence, threshold = 0.7):
    max_score = max(sentence_scores.values())
    threshold = max_score * threshold

    summary_sentences = [s for s, score in sentence_scores.items() if score >= threshold]

    first_sentence = orig_sentence[0]
    if first_sentence not in summary_sentences:
        summary_sentences.insert(0, first_sentence)

    return ' '.join(summary_sentences)

if __name__ == "__main__":
    paragraph = input("Enter a paragraph or claim: ")
    cleaned = clean(paragraph)
    sentences, words = makesometokens(cleaned)
    freq_table = buildfreqtable(words)
    scores = setscores(sentences, freq_table)
    summary = getsummary(scores, sentences)

    for sent, score in sorted(scores.items(), key=lambda x: -x[1]):
        print(f"{score:.2f}: {sent}")

    print("\nSummary:")
    print(summary)

