import re
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity #imports

# selects device for compute, either 1.gpu or 2. cpu
device = "cuda" if torch.cuda.is_available() else "cpu"

# load the custom bert model (legalbert) onto the hardware of choice
tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
model = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased").to(device)
model.eval()

def embed_units(units):
    inputs = tokenizer(
        units,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    ) #this tells the computer how to tokenize input with padding, truncation, and coversion to tensors

    # move the tensors from above into the device of choice (cpu gpu)
    inputs_converted = {}

    for k, v in inputs.items():
        inputs_converted[k] = v.to(device)

    inputs = inputs_converted

    out = model( #run the model and show the last hidden state of tokens, we get a pytorch tensor out
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"]
    ).last_hidden_state

    # takes the mean (average) of embeddings to get a single vector and gives to the cpu
    return out.mean(dim=1).cpu().detach().numpy()

def extractive_summary_with_intro(text, k=3):

    chunks = [] #list for each chunk for tokenization

    # First, split the text on semicolons and commas using regex
    split_units = re.split(r"[;,]", text)

    # Iterage over the newly split
    for u in split_units:
        stripped = u.strip()  # remove whitespace
        if stripped:  # add only strings that have content
            chunks.append(stripped)
    if len(chunks) <= k + 1:
        # if there are too few chunks, just return the original
        return text

    # keep the intro chunk! we need that context
    intro = chunks[0]

    # we will add the remaining chunks
    body_chunks = []
    for i in range(1, len(chunks)):
        body_chunks.append(chunks[i])

    #create an embedding for the body chunks
    embeds = embed_units(body_chunks)
    centroid = embeds.mean(axis=0, keepdims=True) #compute the mean (Average) vector of the embeddings
    scores = cosine_similarity(embeds, centroid).flatten() #calculate the cosine similarity between a specific emedding
    # and the mean embedding vector

    #use numpy/topk to sort top scores and preserves original order
    besttoks = np.argsort(scores)[-k:]
    besttoks.sort()

    #builds our sentence string.
    selected = [intro]
    for i in besttoks:
        selected.append(body_chunks[i])
    return "; ".join(selected) + "."

if __name__ == "__main__":
    orig = (
        "A child motion apparatus comprising: a base frame assembly for providing standing support on a floor; "
        "a column connected with the base frame assembly; a support arm extending generally horizontally relative to the column, "
        "the support arm having a first and a second end portion, the first end portion being assembled with the column and having a channel extending generally vertically, "
        "the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; "
        "a child seat connected with the second end portion of the support arm; a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; "
        "and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, "
        "wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm."
    )
    # orig = " A system comprising: a plurality of slots each configured to receive a modular " \
    #        "information handling system; a plurality of air movers each configured to cool at " \
    #        "least one modular information handling system disposed in at least one of the plurality" \
    #        " of slots; and a controller communicatively coupled to the plurality of slots and the " \
    #        "plurality of air movers and configured to, based on one or more thermal operational" \
    #        " parameters associated with the plurality of slots and the plurality of air movers, " \
    #        "determine an optimal allocation of at least one workload to a particular information " \
    #        "handling system of a plurality of modular information handling systems received in the plurality of" \
    #        " slots, wherein the determining the optimal allocation includes: determining, for each of a " \
    #        "plurality of possible allocations, a corresponding power consumption associated with the plurality" \
    #        " of air movers; and selecting the optimal allocation from the plurality of possible allocations such" \
    #        " that the corresponding power consumption associated with the plurality of air movers is minimized;" \
    #        " wherein the optimal allocation is further based on an airflow impedance ranking of the plurality of" \
    #        " modular information handling systems received in the plurality of slots, wherein the airflow impedance" \
    #        " of each respective modular information handling system is based on an amount of airflow impeded by respective" \
    #        " numbers and types of information handling resources contained in such respective modular information handling system."
    print("Orig:", orig)
    print("\n")
    print("Summary:", extractive_summary_with_intro(orig, k=4))
