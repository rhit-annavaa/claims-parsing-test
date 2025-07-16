import spacy
# from collections import defaultdict


text="A robotic cleaning device comprising a main body, " \
     "a drive system coupled to the main body and configured " \
     "to move the device across a surface, a dust collection " \
     "unit disposed within the main body, a sensor system positioned" \
     " on the main body and configured to detect obstacles, a control " \
     "module in communication with the sensor system and the drive system, " \
     "the control module being configured to navigate the device based on " \
     "signals received from the sensor system, and a cleaning assembly operably" \
     " connected to the dust collection unit and positioned beneath the main body," \
     " wherein the cleaning assembly comprises a rotating brush and a suction inlet " \
     "aligned with the rotating brush, and wherein the control module is further " \
     "configured to deactivate the cleaning assembly when it determines that the " \
     "device is on a carpeted surface."

nlp = spacy.load("en_core_web_small")
doc = nlp(text)

resolved_text = doc._.coref_resolved

noun_phrases = []
doc = nlp(resolved_text)

for chunk in doc.noun_chunks:
    noun_phrases.append(chunk.text)

def getstruct(text):
