import spacy

nlp = spacy.load("en_core_web_lg")

doc1 = nlp(" A child motion apparatus comprising: a base frame assembly for providing standing support on a floor; a column connected with the base frame assembly; a support arm extending generally horizontally relative to the column, the support arm having a first and a second end portion, the first end portion being assembled with the column and having a channel extending generally vertically, the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; a child seat connected with the second end portion of the support arm; a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm.")
doc2 = nlp(" An antenna arrangement for the reception of circularly polarized satellite radio signals in which antenna arrangement an antenna structure having a loop radiator is arranged in a protective antenna cover of plastic, the protective antenna cover having an opening, wherein the protective antenna cover is provided at the inner side with grooves that are open toward the opening and that are adapted to an outer contour of the antenna structure such that it is held with shape matching at least in a peripheral direction in the protective antenna cover after an insertion through the opening.")

print(nlp.pipe_names) #tells us what is going on under the hood, as in, what components are being run when one calls nlp()

print(nlp.pipeline) #name,component

print(doc1.similarity(doc2)) #numerical value 0-1 based on cosine similarities

