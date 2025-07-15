import spacy

nlp = spacy.load("en_coreference_web_trf")
doc = nlp("Amruth plays the tabla because he loves it.")
print(doc.spans)