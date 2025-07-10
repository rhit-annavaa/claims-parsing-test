import spacy

nlp = spacy.load("en_core_web_lg")

doc1 = nlp("I like cats")
doc2 = nlp("I like injury")

print(nlp.pipe_names) #tells us what is going on under the hood, as in, what components are being run when one calls nlp()

print(nlp.pipeline) #name,component

print(doc1.similarity(doc2)) #numerical value 0-1 based on cosine similarities

