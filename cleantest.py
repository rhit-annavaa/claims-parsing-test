import re
import spacy

nlp = spacy.load("en_core_web_lg") #load the large english model from spacy

def extract_claim_elements(text):
    m = re.search(r'comprising\s*:\s*(.*)', text, re.IGNORECASE) #tries to go for everyhting after "comprising"
    if m:
        body = m.group(1)
    else:
        body = text

    parts = re.split(r';\s*', body) #split into segments by ";"

    results = []
    for part in parts:
        seg = part.strip().rstrip('.').strip() #take out periods and whitespace
        if not seg:
            continue #skip if empty


        seg = re.sub(r'^\band\s+', '', seg, flags=re.IGNORECASE) #remove "and"

        #special case for wherein, I think we can add more specific word identifiers going forward
        if re.match(r'wherein\b', seg, re.IGNORECASE):
            doc = nlp(seg)
            # takes the first noun chunk from the spacy model
            first_np = next(doc.noun_chunks, None)
            if first_np: #if there is one
                subj = first_np.text #get the text
                req = re.sub(r'^wherein\s*', '', seg, flags=re.IGNORECASE) #drop the wherein
                req = req[len(subj):].strip(' ,.') #take the rest of the content as a requirement
                results.append({"subject": subj, "requirement": req}) #adds to the results list
            continue

        doc = nlp(seg)#same thing as above, but for any clause, not just "wherein"
        first_np = next(doc.noun_chunks, None)
        if not first_np:
            continue

        subj = first_np.text #take the subject
        start = first_np.end_char #take the start, ie character offset after the subject
        req = seg[start:].strip(' ,.') #get everyhting after the subjec

        results.append({"subject": subj, "requirement": req})

    return results


if __name__ == "__main__":
    # claim = (
        # " A system comprising: a plurality of slots each configured to receive a modular information handling system; "
        # "a plurality of air movers each configured to cool at least one modular information handling system disposed"
        # " in at least one of the plurality of slots; and a controller communicatively coupled to the plurality of"
        # " slots and the plurality of air movers and configured to, based on one or more thermal operational parameters"
        # " associated with the plurality of slots and the plurality of air movers, determine an optimal allocation of at"
        # " least one workload to a particular information handling system of a plurality of modular information handling"
        # " systems received in the plurality of slots, wherein the determining the optimal allocation includes: "
        # "determining, for each of a plurality of possible allocations, a corresponding power consumption associated "
        # "with the plurality of air movers; and selecting the optimal allocation from the plurality of possible allocations"
        # " such that the corresponding power consumption associated with the plurality of air movers is minimized; wherein "
        # "the optimal allocation is further based on an airflow impedance ranking of the plurality of modular information "
        # "handling systems received in the plurality of slots, wherein the airflow impedance of each respective modular "
        # "information handling system is based on an amount of airflow impeded by respective numbers and types of information "
        # "handling resources contained in such respective modular information handling system."
        # "A child motion apparatus comprising: "
        # "a base frame assembly for providing standing support on a floor; "
        # "a column connected with the base frame assembly; "
        # "a support arm extending generally horizontally relative to the column, "
        # "the support arm having a first and a second end portion, "
        # "the first end portion being assembled with the column and having a channel extending generally vertically, "
        # "the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; "
        # "a child seat connected with the second end portion of the support arm; "
        # "a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; "
        # "and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, "
        # "the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, "
        # "wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm."
    # )
    claim= "A substrate transfer apparatus, comprising: a load lock chamber for generating a" \
       " substantially inert environment at about atmospheric pressure and devoid of water" \
       " vapor, the load lock chamber comprising: a chamber body defining a process volume; " \
       "a pedestal disposed in the process volume; a plurality of lift pins disposed about the " \
       "pedestal, wherein a plurality of recesses are formed in the pedestal adjacent to the " \
       "lift pins, and wherein each of the plurality of lift pins comprises a shaft, a first " \
       "extension coupled to and extending from the shaft, a second extension coupled to and " \
       "extending from the shaft, wherein the second extension is disposed adjacent to and " \
       "spaced apart from the first extension; a lid coupled to the chamber body opposite the " \
       "pedestal; a purge gas port disposed through the lid; and an exhaust port disposed in " \
       "the chamber body adjacent to the pedestal and opposite the purge gas port; and a transfer " \
       "chamber for generating a substantially inert environment at about atmospheric pressure" \
       " and devoid of water vapor coupled to the load lock chamber, the transfer chamber comprising: " \
       "a chamber body defining a transfer volume; a robot disposed in the transfer volume; an sensor " \
       "in fluid communication with the transfer volume; a plurality of purge gas ports disposed in the " \
       "chamber body, each of the plurality of purge gas ports having a diffuser extending therefrom, " \
       "the diffuser configured to diffuse gases throughout the chamber body; and an exhaust port disposed" \
       " in the chamber body opposite the plurality of purge gas ports."

    for item in extract_claim_elements(claim):
        print("Subject: " +item['subject'])
        print("Requirement: " + item['requirement'])
        print("-" * 24)
