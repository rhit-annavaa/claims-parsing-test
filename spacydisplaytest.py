import spacy
from spacy import displacy

#absolute fundamentals to get a dependency graph
nlp = spacy.load("en_core_web_lg") #uses this pretrained model from spacy
# doc = nlp("") #this is the text that you will run through the model
# displacy.serve(doc, style="dep") #this will serve at localhost:5000 and display a dependency graph

text = "A child motion apparatus comprising: a" \
       "base frame assembly for providing standing support on a floor; " \
       "a column connected with the base frame assembly; a support arm extending " \
       "generally horizontally relative to the column, the support arm having a first and a " \
       "second end portion, the first end portion being assembled with the column and having a channel extending" \
       " generally vertically, the support arm further being connected with the column via a hinge about which " \
       "the support arm is rotatable generally horizontally relative to the column; a child seat connected with " \
       "the second end portion of the support arm; a vertical actuating mechanism supported by the base frame assembly " \
       "and operable to drive the column to slide upward and downward relative to the base frame assembly; and a horizontal " \
       "actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, " \
       "the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding " \
       "movement along the channel at the first end portion of the support arm, wherein a circular motion of the driving " \
       "part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm."
#full text exmaple ^

doc = nlp(text) #uses the model on the text

# first_token=doc[1] #takes the second chunk given by the nlp

# for token in doc: #looks at each chunk in the doc
#        print(token.text, token.pos_) #prints the chunk and the pos it was assigned


# print(first_token.text) #print the text from the model

sentence_spans = list(doc.sents) #creates a list of sentences
displacy.serve(sentence_spans, style="dep")