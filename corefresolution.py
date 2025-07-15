import spacy
# import neuralcoref

nlp = spacy.load("en_coreference_web_trf") # load the spacy pretrained coreference model

####Below are sample texts, on normal text this code actually works relatively well. But
####on legal text, not so well.

# text="Amruth plays the tabla because he loves it."
text="Sarah handed the book to Jonathan after she finished reading it, but he said he would return it to the library himself."
# text = " A child motion apparatus comprising: " \
#        "a base frame assembly for providing standing support on a floor; " \
#        "a column connected with the base frame assembly; a support arm extending generally " \
#        "horizontally relative to the column, the support arm having a first and a second end portion, " \
#        "the first end portion being assembled with the column and having a channel extending generally vertically, " \
#        "the support arm further being connected with the column via a hinge about which the support arm is rotatable " \
#        "generally horizontally relative to the column; a child seat connected with the second end portion of the support arm;" \
#        " a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and " \
#        "downward relative to the base frame assembly; and a horizontal actuating mechanism operable to drive the support arm to " \
#        "oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable" \
#        " along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, " \
#        "wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an " \
#        "oscillating movement of the support arm."



def resolve(text):
    doc = nlp(text) #process the text w the spacy nlp pipeline
    tokens = []
    for t in doc:
        tokens.append(t.text_with_ws) #adds tokens to the list if they are there
    for key in doc.spans:
        if key.startswith("coref_clusters"): #checks for keys that match the
            cluster=doc.spans[key] #gets the item at the key
            content=cluster[0].text #the subject
            cluster_mentions = list(cluster) #cast the items as a list
            for i in range(1, len(cluster_mentions)):#skips first element which is presumed to be the subject
                mention = cluster_mentions[i]
                tokens[mention.start] = content + doc[mention.start].whitespace_ #substitutes the mention with the main subject and whitespace

                # Gets rid of the rest of the tokens to avoid duplication
                for i in range(mention.start + 1, mention.end):
                    tokens[i] = ""
    print(doc.spans.keys()) #prints keyes
    return "".join(tokens) #



print(nlp.pipe_names)
# print(doc.spans.keys())
print(resolve(text))



