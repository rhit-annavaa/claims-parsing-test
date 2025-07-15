# from gensim.summarization import summarize, keywords
# import gensim
#
#

# summary = summarize(text, ratio = 0.5)
# print(summary)
import os
os.environ["TRANSFORMERS_NO_TF"] = "1" #something about forcing the system to use a particular piece of hardware
from transformers import pipeline
# from tensorflow.keras.layers import Layer

#text sample
text = " A child motion apparatus comprising: " \
       "a base frame assembly for providing standing support on a floor; " \
       "a column connected with the base frame assembly; a support arm extending generally " \
       "horizontally relative to the column, the support arm having a first and a second end portion, " \
       "the first end portion being assembled with the column and having a channel extending generally vertically, " \
       "the support arm further being connected with the column via a hinge about which the support arm is rotatable " \
       "generally horizontally relative to the column; a child seat connected with the second end portion of the support arm;" \
       " a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and " \
       "downward relative to the base frame assembly; and a horizontal actuating mechanism operable to drive the support arm to " \
       "oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable" \
       " along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, " \
       "wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an " \
       "oscillating movement of the support arm."
#
#simple built-in summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn", framework="pt", device=-1) #change 0 for GPU to -1 for CPU only
result = summarizer(text, max_length=130, min_length=30, do_sample=True, top_k=30, top_p=0.92, temperature =0.7) #use the summarizer with up to 130 words.
print(result[0]['summary_text']) 