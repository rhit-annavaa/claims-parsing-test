import nltk
import re
import heapq
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
# from allennlp.predictors.predictor import Predictor
# import allennlp_models.coref
#
#
# ###COREF RESOLUTION STUFF NEW TOO!!!
#
# coref_predictor = Predictor.from_path(
#     "https://storage.googleapis.com/allennlp-public-models/coref-spanbert-large-2021.03.10.tar.gz"
# )


####------------

######NEW STUFF >>>>>
def fetchpreamble(text):
    match = re.search(r"^(.*?\b(?:comprising|including|consisting of)\b)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    else:
        return " "

def fetchelements(text):
    tagged = nltk.pos_tag(word_tokenize(text))
    components = []
    for i in range(len(tagged) - 1):
        word, tag = tagged[i]
        next_word, next_tag = tagged[i + 1]

        if tag in ('DT',) and next_tag.startswith('NN'):
            component = f"{word} {next_word}"
            components.append(component)

    return components

def fetchfunctionality(text):
    matches = re.findall(r"\b(?:configured|adapted|operable|driven)\s+to\s+[^,;\.]+", text, re.IGNORECASE)
    stripped = []
    for m in matches:
        stripped.append(m.strip())
    return stripped

######NEW STUFF ^^^^^^^^--------------------------------------------------------------


def clean(text): #cleans the input
    cleaned_text=re.sub(r'\s+', ' ', text) #looks for white space and scrubs it
    cleaned_text=re.sub(r'\[[0-9]*\]', ' ', cleaned_text) #looks for numerals and cleans them

    return cleaned_text #returns the scrubbed text

def makesometokens(text): #this partitions the input into tokens
    # sentences = sent_tokenize(text)

    rough_sentences = re.split(r'[;,\.]', text) #custom spliting because we dont see a lot of "." in legal documents, so we are looking for semicolons and commas
    sentences = []
    for s in rough_sentences:
        stripped = s.strip()
        if len(stripped) > 5: #____10_____
            sentences.append(stripped) #only keep sentences more than 5 characters

    words = word_tokenize(text.lower())

    return sentences, words

def buildfreqtable(words): #we try to build a occurence frequency table
    stop_words=set(stopwords.words("english")) #skip the stopwords from the default set
    freq_table = {} #create a list

    pos_tags = nltk.pos_tag(words) #uses nltk to tag words with their POS

    for word, pos in pos_tags:
        if word in stop_words: #if the word is a stopword, then get out!
            continue
        if pos.startswith("N"): #if the word is a noun, then it gets more weight
            weight = 1.5
        elif pos.startswith("V"): #same with a verb, but less weight than a noun
            weight = 1.3
        else:
            weight = 1 #otherwise standard multiplier

        freq_table[word]=freq_table.get(word,0)+weight #add the frequency of the word to its index, also including the additional weight

    return freq_table #return the list of word frequencies

def setscores(text, freq_table):
    sentence_scores = {} #create a set for the scores

    for sentence in text: #search the input text for each sentence
        word_count = 0 #tracks the important words' number of occurences in the sentence
        for word in word_tokenize(sentence.lower()): #iterate over the now word tokenized input, also lowercase
            if word in freq_table: #if the word is in the table
                sentence_scores[sentence] = sentence_scores.get(sentence, 0) + freq_table[word] #add the word's frequency including its possible additional weight
                word_count+=1 #add that there was a valid word from the set of frequent words
        if sentence in sentence_scores and word_count > 0: #get the average basically divide the value of the sentence by the number of "important" words
            sentence_scores[sentence] /= word_count

    return sentence_scores #return

#Threshold based sorting

# def getsummary(sentence_scores, orig_sentence, threshold = 0.6): #our threshold is set to 60% of the maximum score achieved
#     max_score = max(sentence_scores.values()) #set the max score to the highest score in the sentence_scores list
#     threshold = max_score * threshold #multiply to determine the threshold
#
#     summary_sentences = [] #these are the sentences we will actually return
#     for sentence, score in sentence_scores.items(): #checks if the score of a given sentence is higher than the threshold
#         if score >= threshold:
#             summary_sentences.append(sentence) #if it is, then add it to the list of summaries
#
#     first_sentence = orig_sentence[0] #i I want to force the program to add the first sentence to the beginning, sometimes
#     if first_sentence not in summary_sentences: #the program will deem the first sentence below the threshold, and we end up
#         summary_sentences.insert(0, first_sentence) #losing that sentence which has a lot of important context in most cases
#
#     return ' '.join(summary_sentences) #lastly we are just joining everyting together with a ' ' inbetween each phrase

#top-k based soting
def getsummary(sentence_scores, orig_sentences, top_k=9):
    top_sentences = heapq.nlargest(top_k, sentence_scores.items(), key=lambda x:x[1]) #we look for
    #the highest top-k scoring sentences. Then we want to sort the items by the score

    summary_sentences = [] #creates a list of sentence strings
    for s in top_sentences:
        sentence = s[0] #selects the sentence not the score
        summary_sentences.append(sentence) #adds the sentnece to the string

    sorted_summary_sentences = [] #go back thru the list
    for s in orig_sentences:
        if s in summary_sentences:
            sorted_summary_sentences.append(s) #add the sentence to the list if it
            #exists in the top sentences. we do this because then the original order is preserved instead of top-k order

    first_sentence = orig_sentences[0] #i I want to force the program to add the first sentence to the beginning, sometimes
    if first_sentence not in sorted_summary_sentences: #the program will deem the first sentence below the threshold, and we end up
        sorted_summary_sentences.insert(0, first_sentence) #losing that sentence which has a lot of important context in most cases

    final_summary = ''
    for sentence in sorted_summary_sentences:
        final_summary += sentence + ' '

    return final_summary





if __name__ == "__main__": #main method
    paragraph = input("Enter a paragraph or claim: ") #user input instead of json

    #new stuff >>>>
    preamble = fetchpreamble(paragraph)
    print("\nPreamble:")
    print(preamble)

    components = fetchelements(paragraph)
    print("\nComponents:")
    for c in sorted(set(components)):
        print(f"- {c}")

    functionality = fetchfunctionality(paragraph)
    print("\nFunctionality:")
    print(functionality)
    print("\n")

    cleaned = clean(paragraph) #run all of our methods
    sentences, words = makesometokens(cleaned)
    freq_table = buildfreqtable(words)
    scores = setscores(sentences, freq_table)
    summary = getsummary(scores, sentences)

    for sent, score in sorted(scores.items(), key=lambda x: -x[1]): #I also want to print the scores
        print(f"{score:.2f}: {sent}")                               #for sentnceses in order so I can
                                                                    #get a better idea of whats going on
    print("\nSummary:") #print out the summary to the cmd line
    print(summary)

