import re
from collections import defaultdict
from typing import Dict, List

import spacy

nlp = spacy.load("en_core_web_md") #load med spacy model

#terms to track transitions/clause splits, we can add to this dynamically
TRANSITION_TERMS = [
    "comprising",
    "comprises",
    "comprise",
    "including",
    "includes",
    "contain",
    "containing",
    "contains",
    "characterized by",
    "consisting of",
    "consist of",
    "consists of",
    "consisting essentially of",
    "consist essentially of",
    "having",
    "has",
]


def normalize(text):
    text = text.lower().strip()#lowercae and strip leading/trailing space
    text = re.sub(r"^(the|a|an)\s+", "", text) #rid of a,an,the
    text = re.sub(r"[^\w\s]", "", text)
    return text#return scrubbed content


def format_requirement(req):
    req = req.strip().rstrip(",.")#gets rid of more space
    if req:
        req = req[0].upper() + req[1:]#capitalizes first letter of first word
    if not req.endswith('.'):
        req += '.' #add period to the end
    return req #return newly formatted sentence


def extract_body(text):
    # remove leading distinctions like numbers or letters
    text = re.sub(r"^\s*(\d+\.|\([a-zA-Z]\)|[a-zA-Z]\))\s*", "", text).strip()

    escaped_terms = []
    for t in TRANSITION_TERMS:
        escaped_terms.append(re.escape(t)) #searches for terms that can be used safely in regular expressions

    pattern = re.compile(
        r"\b(?:" + "|".join(escaped_terms) + r")\b\s*[:,-]?\s*(.*)",
        flags=re.IGNORECASE | re.DOTALL,
    ) #we basically check if a whole word is a transition word and finds the text after it
    m = pattern.search(text) #searches using the pattern defined above
    if m:
        body = m.group(1) #sets body to the text following the transition word
    else:
        body = text
    return body.strip() #return the fully stripped body text


def split_segs(body):
    candidates = re.split(r";\s*", body) #split the input text on semicolons
    parts: List[str] = []
    for cand in candidates: #goes thru the text
        seg = cand.strip() #strips the segment we are in
        if not seg:
            continue #skips if theres no content
        seg = re.sub(r"^(and|or)\s+", "", seg, flags=re.IGNORECASE) #remove leading and, or
        parts.append(seg) #add the newly split term to the list
    return parts #return the list of newly split parts


def where_splits(part):
    # we search for specific subclause terms here
    where_terms = ["wherein", "whereby"]
    tokens = re.split(
        r"(\b(?:" + "|".join(where_terms) + r")\b)", part, flags=re.IGNORECASE
    ) #split on these new custom terms
    segments: List[str] = []
    buffer = ""
    in_where = False
    for tok in tokens:
        if re.fullmatch(r"\b(?:" + "|".join(where_terms) + r")\b", tok, flags=re.IGNORECASE): #if there is a match with a search term
            if buffer: #and if there is content in the buffer
                segments.append(buffer) #add the buffer content as a segment
            buffer = tok  # start a new subclause by setting the buffer to the current token
            in_where = True #flag to indicate we are in a werein/whereby clause
        else:
            if in_where:
                # append this token (text) to the subclause and remove it
                buffer += " " + tok
                segments.append(buffer)
                buffer = ""
                in_where = False
            else:
                buffer = tok
    if buffer:
        segments.append(buffer)

    #Further filtering looking for commas, we are doing everything we can to take on the unique legal langugae/grammar
    final: List[str] = []
    for seg in segments:
        final.extend(re.split(r",\s*", seg))
    result = []
    for seg in final:
        s = seg.strip()
        if s:
            result.append(s)
    return result


def split_reqs(req):
    doc = nlp(req) #run the model
    # we search for the root token
    root = None
    for tok in doc:
        if tok.head == tok:
            root = tok
            break
    if not root:
        return [req.strip(" ,.")]

    # get the root and its associated conjunctions
    heads = [root] + list(root.conjuncts)

    # Find tokens belonging to sub-conjunctions
    conj_subtrees = set() #we use a set because there are no duplicates in sets!
    for c in root.conjuncts:
        for tok in c.subtree:
            conj_subtrees.add(tok)

    independent: List[str] = []
    for head in heads: #root tokens
        tokens = []
        for t in head.subtree:
            # skip coordinating conjunction tokens in the subtree
            if t.dep_ == "cc":
                continue
            # avoid overlapping subtrees
            if head is root and t in conj_subtrees:
                continue
            tokens.append(t)
        if tokens:
            # sort tokens by their position in the doc
            tokens = sorted(tokens, key=lambda x: x.i)
            phrase = " ".join(t.text for t in tokens).strip(" ,.")
            independent.append(phrase)

    # fallback: two clause fallback (i.e. a brown fox and a fast car)
    if len(independent) <= 1: #only starts if the clause hasnt alr been split
        np_pattern = re.compile(
            r"^(?P<prefix>.*?\b)(?P<det1>a|the)\s+(?P<adj1>\w+)\s+and\s+(?P<det2>a|the)\s+(?P<adj2>\w+)\s+(?P<noun>.+)$",
            flags=re.IGNORECASE,
        ) #follows the specific pattern
        m = np_pattern.match(req)
        if m: #if there is a match then custom build these two phrases
            pre = m.group('prefix').strip()
            det1, adj1 = m.group('det1'), m.group('adj1')
            det2, adj2 = m.group('det2'), m.group('adj2')
            noun = m.group('noun').strip()
            independent = [
                "{} {} {} {}".format(pre, det1, adj1, noun).strip(),
                "{} {} {} {}".format(pre, det2, adj2, noun).strip(),
            ]

    # second falback: just split on and
    if len(independent) <= 1 and re.search(r"\b and \b", req, re.IGNORECASE):
        parts = re.split(r"\b and \b", req, flags=re.IGNORECASE)
        if len(parts) == 2: #assuming the clause evenly got split on the "and" resulting in two seperate clauses
            independent = []
            for p in parts:
                independent.append(p.strip())

    # Remove empty strings and return
    result = []
    for r in independent:
        if r:
            result.append(r)
    return result


def get_claims(text):
    body = extract_body(text) #grab the body text

    parts = split_segs(body)
    raw_results: List[Dict[str, object]] = []
    idx = 0
    for part in parts:
        # search for "wherein"/"whereby" subclauses within the parts
        segments = where_splits(part)
        for seg in segments:
            seg = seg.strip().rstrip('.')
            if not seg:
                continue
            # Omit leading "and" from the segment
            seg = re.sub(r"^\band\s+", "", seg, flags=re.IGNORECASE)
            # Discern if this is a subclause using this identifier language
            if re.match(r"^(wherein|whereby)\b", seg, flags=re.IGNORECASE):
                doc = nlp(seg)
                np = next(doc.noun_chunks, None) #find the noun chunks
                if not np: #if there arent any
                    continue
                subj = np.text #we take the nounchunk to be the subject
                # requirement is the remainder of the clause after the subject
                req = seg[len(np.text):].strip()#get rid of np and whitespace
                req = re.sub(r"^\b(?:wherein|whereby)\b", "", req, flags=re.IGNORECASE).strip(' ,') #get rid of legal wording
                for ar in split_reqs(req):
                    raw_results.append({"subject": subj, "requirement": ar, "index": idx})
                    idx += 1 #track the index of the newly appended results
            else:
                # extract the first noun phrase as the subject
                doc = nlp(seg)
                np = next(doc.noun_chunks, None)
                if not np:
                    continue
                subj = np.text
                req = seg[np.end_char:].strip(' ,')
                for ar in split_reqs(req):
                    raw_results.append({"subject": subj, "requirement": ar, "index": idx})
                    idx += 1

    # Undo any duplication
    seen = set()
    unique: List[Dict[str, object]] = []
    for it in raw_results:
        key = (normalize(it['subject']), it['requirement'].lower()) #subject, requirement format to be added to the list
        if key not in seen: #add new keyes
            seen.add(key)
            unique.append(it)

    final_results: List[Dict[str, object]] = [] #this is a formatted list with info as follows: [sub, req, idx]
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list) #this is a dict that maps normalized subjects to their associated items
    for it in unique:
        grouped[normalize(it['subject'])].append(it) #dict of subject/req grouped by items that refer to the same objext

    for norm_subj, items in grouped.items(): #now that we have the subject groups
        reqs = [i['requirement'] for i in items]
        filtered: List[str] = []
        for r in reqs:#we take a requirement
            redundant = False
            for o in reqs: #and compare it to every other requirment
                if r != o and r in o:
                    redundant = True
                    break #if they are the same then mark as redundant
            if not redundant:
                filtered.append(r) #otherwise append
        for r in filtered:
            orig_subj = None# Retrieve the original subject and index from one of the items
            index = None
            for i in items:
                if i['requirement'] == r:
                    orig_subj = i['subject']
                    index = i['index']
                    break
            final_results.append({"subject": orig_subj, "requirement": r, "index": index}) #append a clean dict to the final output

    return sorted(final_results, key=lambda x: x['index']) #return the list sorted by the idx


def build_claim_tree(elements):
    nodes: Dict[str, Dict[str, object]] = {} # This stores each subject as a dict with [subject, req, children]
    for el in elements:
        key = normalize(el['subject']) #populate the list
        if key not in nodes:
            nodes[key] = {
                'subject': el['subject'],
                'requirements': [],
                'children': [],
            }
        nodes[key]['requirements'].append(el['requirement'])#add requirements

    # case:"having/including/comprising ..." patterns
    parent_of: Dict[str, str] = {}
    for el in elements:
        subj_key = normalize(el['subject']) #normalize the subject
        req = el['requirement'].lower().strip() #essentially standardzing the requirnemtn text too
        # case: node has child
        m1 = re.match(
            r'(?:having|including|comprising|includes|consisting of)\s+'
            r'(?:a|an|the)\s+(.*)',
            req,
        )#searches for these clauses in reqs because they could be indicative of a child component
        if m1:#if there is a case
            child_phrase = m1.group(1).strip().rstrip('.')#we find and isolate the phrase
            child_candidate = re.split(r'\b and \b', child_phrase)[0].strip()
            child_key = normalize(child_candidate)
            if child_key in nodes and child_key != subj_key:
                parent_of.setdefault(child_key, subj_key)
            continue  # skip the next case
        # case: subject is connected or supported by parent
        m2 = re.match(
            r'(?:connected with|connected to|coupled to|attached to|supported by|supported on)\s+'
            r'(?:the|a|an)\s+(.*)',
            req,
        )
        if m2: #for case 2
            parent_phrase = m2.group(1).strip().rstrip('.') #get the parent NP
            parent_candidate = None
            for key in sorted(nodes.keys(), key=lambda k: -len(k)): #finds the closest matching subject key
                if key == subj_key:
                    continue
                if key in normalize(parent_phrase):
                    parent_candidate = key
                    break
            if parent_candidate:
                # record the parent match
                parent_of.setdefault(subj_key, parent_candidate) #setdefault ensures we don't overwrite a preexisting assingmnet

    # match the parents to children
    roots: List[Dict[str, object]] = []
    for key, node in nodes.items():
        if key in parent_of:
            parent_key = parent_of[key]
            if parent_key in nodes:
                nodes[parent_key]['children'].append(node)
        else:
            roots.append(node)
    return roots


def _print_claim_tree(node, indent: int = 0):
    indent_str = '  ' * indent #start with zero indent for primary subjects
    print(indent_str + "Subject: " + node['subject']) #print subject
    for req in node['requirements']: #print requiremnst
        print(indent_str + "  - " + format_requirement(req))
    for child in node['children']:
        _print_claim_tree(child, indent + 1) #print children with an indent


if __name__ == "__main__":
    sample_claim = (
        "1. A child motion apparatus comprising: a base frame assembly for providing "
        "standing support on a floor; a column connected with the base frame "
        "assembly; a support arm extending generally horizontally relative to the "
        "column, the support arm having a first and a second end portion, the first "
        "end portion being assembled with the column and having a channel extending "
        "generally vertically, the support arm further being connected with the "
        "column via a hinge about which the support arm is rotatable generally "
        "horizontally relative to the column; a child seat connected with the "
        "second end portion of the support arm; a vertical actuating mechanism "
        "supported by the base frame assembly and operable to drive the column to "
        "slide upward and downward relative to the base frame assembly; and a "
        "horizontal actuating mechanism operable to drive the support arm to "
        "oscillate generally horizontally relative to the column, the horizontal "
        "actuating mechanism including a driving part movable along a circular "
        "path and guided for sliding movement along the channel at the first end "
        "portion of the support arm, wherein a circular motion of the driving part "
        "causes the driving part to slide along the channel and thereby drives an "
        "oscillating movement of the support arm."
    )
    elements = get_claims(sample_claim)
    # old prints
    # grouped = defaultdict(list)
    # subj_display: Dict[str, str] = {}
    # for el in elements:
    #     k = normalize(el['subject'])
    #     grouped[k].append(el['requirement'])
    #     subj_display[k] = el['subject']
    # print("Flat summary of claim:\n")
    # for k, reqs in grouped.items():
    #     print(f"Subject: {subj_display[k]}")
    #     for r in reqs:
    #         print(f"  - {format_requirement(r)}")
    #     print("-" * 40)
    #hierchy:
    print("\nSummary of claims:\n")
    roots = build_claim_tree(elements)
    for root in roots:
        _print_claim_tree(root)
        print("-" * 40)