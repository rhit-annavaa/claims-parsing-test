import re
import spacy

nlp = spacy.load("en_core_web_lg")  # load the large English model

def extract_claim_elements(text):
    m = re.search(r'comprising\s*:\s*(.*)', text, re.IGNORECASE)#we are going to isolate teh claim that comes after comprising
    if m:
        # grab the stuff after comprising
        body = m.group(1)
    else:
        # grab the entire text
        body = text

    #we are goning to split on ";"
    parts = re.split(r';\s*', body)
    results = []

    for part in parts:
        tokens = re.split(r'(\bwherein\b)', part, flags=re.IGNORECASE)#this now looks for further embedded subclauses using the wherein identifier
        subparts = []
        buf = ""
        in_wherein = False

        for tok in tokens:
            if re.match(r'\bwherein\b', tok, re.IGNORECASE): #again we look for wherein clause splits inside of the split we already made
                if buf: # basically this logic makes it so that if we find the wherein in the clauses, we pull the wherein and the content after it
                    subparts.append(buf)
                buf = "wherein" #add that first word to the buf
                in_wherein = True #we want to let the program know we are in a wherein clause
            else:
                if in_wherein:
                    buf += " " + tok
                    subparts.append(buf)
                    buf = ""
                    in_wherein = False #append the buf then leave the wherein clause
                else:
                    buf = tok
        if buf:
            subparts.append(buf) # assuming there is something in the bufer then we can add it to the subparts list

        #we can also split on commas in addition to semicolons
        final_segs = []
        for sp in subparts:
            final_segs.extend(re.split(r',\s*', sp))

        # 4. now, with our finally segmented input, we can clean up whitespace etc
        for seg in final_segs:
            seg = seg.strip().rstrip('.').strip()
            if not seg:
                continue
            seg = re.sub(r'^\band\s+', '', seg, flags=re.IGNORECASE)

            # now we check for wherein and we use SpaCy to grab the noun chunk, we then treat the rest as a requirement
            if re.match(r'wherein\b', seg, re.IGNORECASE):
                doc = nlp(seg)
                first_np = next(doc.noun_chunks, None)
                if first_np:
                    subj = first_np.text
                    req = re.sub(r'^wherein\s*', '', seg, flags=re.IGNORECASE)
                    req = req[len(subj):].strip(' ,.')
                    results.append({"subject": subj, "requirement": req})
                continue

            # this is for clauses that don't have wherein
            doc = nlp(seg)
            first_np = next(doc.noun_chunks, None)
            if not first_np:
                continue
            subj = first_np.text
            start = first_np.end_char
            req = seg[start:].strip(' ,.')
            results.append({"subject": subj, "requirement": req})

    return results


if __name__ == "__main__":
    claim = (
        # " A system comprising: a plurality of slots each configured to receive a modular information handling system; "
        # "a plurality of air movers each configured to cool at least one modular information handling system disposed "
        # "in at least one of the plurality of slots; and a controller communicatively coupled to the plurality of slots"
        # " and the plurality of air movers and configured to, based on one or more thermal operational parameters associated "
        # "with the plurality of slots and the plurality of air movers, determine an optimal allocation of at least one"
        # " workload to a particular information handling system of a plurality of modular information handling systems"
        # " received in the plurality of slots, wherein the determining the optimal allocation includes: determining,"
        # " for each of a plurality of possible allocations, a corresponding power consumption associated with the plurality"
        # " of air movers; and selecting the optimal allocation from the plurality of possible allocations such that the"
        # " corresponding power consumption associated with the plurality of air movers is minimized; wherein the optimal "
        # "allocation is further based on an airflow impedance ranking of the plurality of modular information handling systems "
        # "received in the plurality of slots, wherein the airflow impedance of each respective modular information handling "
        # "system is based on an amount of airflow impeded by respective numbers and types of information handling resources "
        # "contained in such respective modular information handling system."
        "A child motion apparatus comprising: "
        "a base frame assembly for providing standing support on a floor; "
        "a column connected with the base frame assembly; "
        "a support arm extending generally horizontally relative to the column, "
        "the support arm having a first and a second end portion, "
        "the first end portion being assembled with the column and having a channel extending generally vertically, "
        "the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; "
        "a child seat connected with the second end portion of the support arm; "
        "a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; "
        "and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, "
        "the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, "
        "wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm."
    )

    for item in extract_claim_elements(claim):
        print(f"Subject: {item['subject']}")
        print(f"Requirement: {item['requirement']}")
        print("-" * 40)
