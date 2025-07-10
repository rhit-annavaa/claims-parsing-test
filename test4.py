import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk import pos_tag
import re

# downloads
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('averaged_perceptron_tagger_eng')

# define stopwords for legal context
legal_stopwords = set(stopwords.words('english')) - {"said", "comprising", "wherein", "configured"}

def split_sentences(pg):
    return re.split(r';\s*|\bcomprisng\b', pg) #split sentences according to semicolons and "comprising, wherein"

