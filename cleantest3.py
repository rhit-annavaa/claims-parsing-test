import re
import spacy
from collections import defaultdict

#spacy large model
nlp = spacy.load("en_core_web_lg")

def normalize(text):
    text = text.lower().strip() #lowercase and get rid of leading space
    text = re.sub(r'^(the|a|an)\s+', '', text) #get rid of articles
    text = re.sub(r'[^\w\s]', '', text) #get rid of punc
    return text#return normalized text

def format_requirement(req): #this essentially makes the text readable by
    req = req.strip().rstrip(",.") #adding back punc at the right place and capitalizing
    if req and req[0].islower():
        req = req[0].upper() + req[1:]
    if not req.endswith('.'):
        req += '.'
    return req #return the newly correctly formed sentence

def split_requirements(req):
    doc = nlp(req) #use the spacy engine on the text
    root = None
    for tok in doc: #searches for root token
        if tok.head == tok:
            root = tok
            break
    if not root: #if there is no root then return
        return [req.strip(" ,.")]

    heads = []
    heads.append(root) #include the tokens connected to the token by a conjunction
    for conj in root.conjuncts:
        heads.append(conj) #add the tokens to the list

    ind_reqs = [] #start a list for independent requirements
    conj_subtrees = set() #start a set for the conjunctions
    for c in root.conjuncts: #identify the subtokens of conjunctions
        for tok in c.subtree:
            conj_subtrees.add(tok)

    for head in heads: #searches thru each phraes to get individual requirements
        tokens = []
        for t in head.subtree: #looks thru all tokens associated with the given head we are in
            if t.dep_ == 'cc': #coordinating conjunction, we skip these
                continue
            if head is root and t in conj_subtrees: #we can skip overlaps with conjunctions
                continue
            tokens.append(t) #add the token to the list if it passes all the above conditions
        if tokens: #go thru the tokens list
            tokens = sorted(tokens, key=lambda t: t.i) #
            token_texts = [] #token list
            for t in tokens: #add the text from the tokens to the list
                token_texts.append(t.text)
            joined = " ".join(token_texts)
            phrase = joined.strip(" ,.")
            ind_reqs.append(phrase)

    # fallback
    if len(ind_reqs) <= 1: #checks if there are not enough individual requirements
        np_pattern = re.compile(
            r'^(?P<prefix>.*?\b)(?P<det1>a|the)\s+(?P<adj1>\w+)\s+and\s+(?P<det2>a|the)\s+(?P<adj2>\w+)\s+(?P<noun>.+)$',
            flags=re.IGNORECASE
        ) #uses regex to break down a given clause
        m = np_pattern.match(req) #try to match the current req string against the pattern
        if m: #if succesful basically extract the individual components
            pre = m.group('prefix').strip() #getting the prefix
            det1, adj1 = m.group('det1'), m.group('adj1') # getting det and adj
            det2, adj2 = m.group('det2'), m.group('adj2')
            noun = m.group('noun').strip()#getting the end portion
            ind_reqs = [
                (pre + det1 + " " + adj1 + " " + noun).strip(), #add the stuff to the requirements list
                (pre + det2 + " " + adj2 + " " + noun).strip(),
            ]

    # fallback
    if len(ind_reqs) <= 1 and re.search(r'\b and \b', req, re.IGNORECASE): #looks for "and" case
        parts = re.split(r'\b and \b', req, flags=re.IGNORECASE) #
        if len(parts) == 2: #this specifically searches the two clauses before and after the "and"
            ind_reqs = [parts[0].strip(), parts[1].strip()]

    result = []
    for a in ind_reqs:
        if a:
            result.append(a) #add the terms from the individual requirements list to the results list
    return result

def get_claims(text):
    m = re.search(r'comprising\s*:\s*(.*)', text, re.IGNORECASE) #isolate the stuff following comprising
    if m:
        body = m.group(1) #if there still content that becomes the body
    else:
        body = text #otherwise it all becomes the body

    parts = re.split(r';\s*', body) #split on semicolons
    raw = [] #holds subj, req
    idx = 0 #tracks order of ids

    for part in parts:
        tokens = re.split(r'(\bwherein\b)', part, flags=re.IGNORECASE) #take care of the wherein references
        segs = []
        buf = ""
        in_where=False #use these vars to collect all segments in a part
        for tok in tokens:
            if re.match(r'\bwherein\b', tok, re.IGNORECASE): #assuming the current token is wherein
                if buf: segs.append(buf) #attach stuff from the buffer into the segs
                buf = "wherein" #
                in_where = True#mark that we are in a wherein clause
            else:
                if in_where:
                    buf += " " + tok
                    segs.append(buf)
                    buf = ""
                    in_where = False #add all the stuff then "leave" the wherein clause
                else:
                    buf = tok
        if buf: segs.append(buf) #add the remainder of the buffer after the loop

        fin = []
        for s in segs: #now we split on commas
            fin.extend(re.split(r',\s*', s))

        for seg in fin:
            seg = seg.strip().rstrip('.').strip() #cleaning whitepsace and empty segs
            if not seg:
                continue
            seg = re.sub(r'^\band\s+', '', seg, flags=re.IGNORECASE) #basically procesing, similar to before

            if re.match(r'wherein\b', seg, re.IGNORECASE): #we now use spacy to find noun chunks
                doc = nlp(seg)
                np = next(doc.noun_chunks, None) #grab the subject of the phrase
                if not np: #go ahead if theres nothing
                    continue
                subj = np.text #this is the actual text without the sub
                req = seg[len('wherein'):].strip()
                req = re.sub(r'^' + re.escape(subj), '', req, flags=re.IGNORECASE).strip(' ,')  #get everyhting excluding the subject
                for ar in split_requirements(req): #we use our own func to break down requirements
                    raw.append({"subject": subj, "requirement": ar, "index": idx})
                    idx += 1
            else: #for non wherein clauses
                doc = nlp(seg)
                np = next(doc.noun_chunks, None)
                if not np:
                    continue
                subj = np.text
                req = seg[np.end_char:].strip(' ,') #same stuff as above but just for base clauses
                for ar in split_requirements(req):
                    raw.append({"subject": subj, "requirement": ar, "index": idx})
                    idx += 1

    # we use this to remove any duplicates that mightve arised
    seen = set()
    unique = []
    for it in raw:
        key = (normalize(it['subject']), it['requirement'].lower()) #normaliing here makes matches more reliable because its not 1-1 syntax sometimes
        if key not in seen:
            seen.add(key)
            unique.append(it)

    # remove redundancy
    final = []
    grouped_by_subject = defaultdict(list)
    for it in unique:
        grouped_by_subject[normalize(it['subject'])].append(it) #group items by normalized subject

    for norm_subj in grouped_by_subject:
        items = grouped_by_subject[norm_subj]

        # extract the requirements for this subject group
        reqs = []
        for i in items:
            reqs.append(i["requirement"])

        # remove redundant substrings
        filtered = []
        for r in reqs:
            is_redundant = False
            for o in reqs:
                if r != o and r in o:
                    is_redundant = True
                    break
            if not is_redundant:
                filtered.append(r)

        #  recover the original subject and index for the remaining strings
        for r in filtered:
            orig_subj = None
            index = None
            for i in items:
                if i["requirement"] == r:
                    orig_subj = i["subject"]
                    index = i["index"]
                    break

            # add cleaned version to the final
            final.append({
                "subject": orig_subj,
                "requirement": r,
                "index": index
            })

    return sorted(final, key=lambda x: x["index"])


if __name__ == "__main__":
    claim = (
        " A child motion apparatus comprising: a base frame assembly for providing standing support on a floor; a column connected with the base frame assembly; a support arm extending generally horizontally relative to the column, the support arm having a first and a second end portion, the first end portion being assembled with the column and having a channel extending generally vertically, the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; a child seat connected with the second end portion of the support arm; a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm."
    )

    elements = get_claims(claim)

    # group for output normalized subjects
    grouped = defaultdict(list)
    subj_display = {}
    for el in elements:
        key = normalize(el["subject"])
        grouped[key].append(el["requirement"])
        subj_display[key] = el["subject"]

    print(f"Summary of Claim (total subjects: {len(grouped)}):\n")
    for key, reqs in grouped.items():
        print(f"Subject: {subj_display[key]}")
        for r in reqs:
            print(f"  - {format_requirement(r)}")
        print("-" * 40)
