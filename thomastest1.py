import spacy
from collections import defaultdict

#we have two different models, one is a transformer that does the coreference resolution
nlp_coref = spacy.load("en_coreference_web_trf")
nlp_parse = spacy.load("en_core_web_lg")
#this other model is used to parse the parts of speech of the given text

text = "A substrate transfer apparatus, comprising: a load lock chamber for generating a" \
       " substantially inert environment at about atmospheric pressure and devoid of water" \
       " vapor, the load lock chamber comprising: a chamber body defining a process volume; " \
       "a pedestal disposed in the process volume; a plurality of lift pins disposed about the " \
       "pedestal, wherein a plurality of recesses are formed in the pedestal adjacent to the " \
       "lift pins, and wherein each of the plurality of lift pins comprises a shaft, a first " \
       "extension coupled to and extending from the shaft, a second extension coupled to and " \
       "extending from the shaft, wherein the second extension is disposed adjacent to and " \
       "spaced apart from the first extension; a lid coupled to the chamber body opposite the " \
       "pedestal; a purge gas port disposed through the lid; and an exhaust port disposed in " \
       "the chamber body adjacent to the pedestal and opposite the purge gas port; and a transfer " \
       "chamber for generating a substantially inert environment at about atmospheric pressure" \
       " and devoid of water vapor coupled to the load lock chamber, the transfer chamber comprising: " \
       "a chamber body defining a transfer volume; a robot disposed in the transfer volume; an sensor " \
       "in fluid communication with the transfer volume; a plurality of purge gas ports disposed in the " \
       "chamber body, each of the plurality of purge gas ports having a diffuser extending therefrom, " \
       "the diffuser configured to diffuse gases throughout the chamber body; and an exhaust port disposed" \
       " in the chamber body opposite the plurality of purge gas ports."

def resolvereferences(text):
    doc = nlp_coref(text)  # process the text w the spacy nlp pipeline

    tokens = []
    for t in doc:
        tokens.append(t.text_with_ws)  # adds tokens to the list if they are there
    for key in doc.spans:
        if key.startswith("coref_clusters"):  # checks for keys that match the expected output format of the keys
            cluster = doc.spans[key]  # gets the item at the key
            content = cluster[0].text  # the subject
            cluster_mentions = list(cluster)  # cast the items as a list
            for i in range(1, len(cluster_mentions)):  # skips first element which is presumed to be the subject
                mention = cluster_mentions[i]
                if doc[mention.start:mention.end].text != content:
                    tokens[mention.start] = content + doc[mention.start].whitespace_
                    for i in range(mention.start + 1, mention.end):
                        tokens[i] = ""  # substitutes the mention with the main subject and whitespace

                # Gets rid of the rest of the tokens to avoid duplication
                for i in range(mention.start + 1, mention.end):
                    tokens[i] = ""
    # print(doc.spans.keys())  # prints keyes
    return "".join(tokens)  #reassembles the modified tokens into one string

def getattributes(text):
    doc = nlp_parse(text) #we use the other language model here
    np_info = defaultdict(set)  # Use set to auto-remove duplicates

    for chunk in doc.noun_chunks: #this is where the noun chunking is stored in the doc object
        np = chunk.text.strip() #we assign the noun phrase to the raw noun chunk
        np_root = chunk.root #we get the grammatical head (core meaning)

        # if the noun/np is the subject of a verb, link the np to the verb
        if np_root.dep_ in ("nsubj", "dobj", "nsubjpass", "acl", "relcl") and np_root.head.pos_ == "VERB":
            np_info[np].add("verb:" + np_root.head.lemma_) #note here that _lemma refers to the base of a word (running -> run)

        # looks for describers connected to the np (adjectives)
        for token in chunk:
            if token.dep_ in ("amod", "compound", "nummod") and token.head == np_root:
                np_info[np].add("modifier:" + token.text)

        # this looks for prepositional phrases (preps relate a noun to other clauses/nouns/words)
        for token in np_root.children:
            if token.dep_ == "prep": #preposition prase keyword
                pp_tokens = []
                for t in token.subtree: #
                    pp_tokens.append(t.text_with_ws)
                pp = " ".join(pp_tokens)
                np_info[np].add("prep phrase: " + pp)

    result = {}
    for k, v in np_info.items(): #key and value (noun/np and attributes)
        v_list = list(v)  # set -> list
        result[k] = v_list  # assign values properly
    return result #sort the results

def printattributes(attributes):
    for np in sorted(attributes):
        print("NP:", np)

        for feat in sorted(attributes[np]):
            print("-", feat) #just a quick way to print everything in a nice way

resolved = (resolvereferences(text))
attr = getattributes(resolved)
printattributes(attr)

