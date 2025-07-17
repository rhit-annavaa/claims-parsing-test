import spacy
import coreferee
from collections import defaultdict

nlp = spacy.load("en_coreference_web_trf")
# nlp.add_pipe("coreferee")
#
text = "Thomas ran to the store because he was hungry, luckily Tina was willing to give him free bread because she is nice!"

def resolvereferences(text):
    doc = nlp(text)  # process the text w the spacy nlp pipeline

    tokens = []
    for t in doc:
        tokens.append(t.text_with_ws)  # adds tokens to the list if they are there
    for key in doc.spans:
        if key.startswith("coref_clusters"):  # checks for keys that match the
            cluster = doc.spans[key]  # gets the item at the key
            content = cluster[0].text  # the subject
            cluster_mentions = list(cluster)  # cast the items as a list
            for i in range(1, len(cluster_mentions)):  # skips first element which is presumed to be the subject
                mention = cluster_mentions[i]
                tokens[mention.start] = content + doc[
                    mention.start].whitespace_  # substitutes the mention with the main subject and whitespace

                # Gets rid of the rest of the tokens to avoid duplication
                for i in range(mention.start + 1, mention.end):
                    tokens[i] = ""
    print(doc.spans.keys())  # prints keyes
    return "".join(tokens)  #

print(resolvereferences(text))