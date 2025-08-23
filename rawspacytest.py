import re
import spacy
from typing import List, Tuple, Dict, Any

#we are looking for these types of POS
VERBISH_POS = {"VERB", "AUX"} #we treat these as verbs
CONTENT_POS = {"VERB", "NOUN", "PROPN", "ADJ"} #we treat these as "content"
CLAUSE_DEPS = {"relcl", "acl", "advcl", "ccomp", "xcomp"} #clauses


def split_top_level_semicolons(s):
    parts, buf, stack = [], [], [] #define the lists for parts, buffer, and the stack: tracks bracket nesting
    pairs = {')': '(', ']': '[', '}': '{'} #lookup table to match parenthesis, brackets, and braces
    for ch in s: #look thru input, single out chars
        if ch in '([{': stack.append(ch) #add opening brackets etc
        elif ch in ')]}':
            if stack and stack[-1] == pairs[ch]: stack.pop() #
        if ch == ';' and not stack:
            seg = ''.join(buf).strip()
            if seg: parts.append(seg)
            buf = []
        else:
            buf.append(ch)
    if buf:
        seg = ''.join(buf).strip()
        if seg: parts.append(seg)
    return [re.sub(r'^\s*(?:,?\s*(?:and|or))\s+', '', p, flags=re.I).strip(' ,.') for p in parts]

def detect_head(text, nlp):
    colon = text.find(':') #search for early splits on colons
    semi = text.find(';') #or semicolons
    if colon != -1 and (semi == -1 or colon < semi): #
        return text[:colon].strip(' ,.'), text[colon+1:].lstrip(' ,.') #we split so that the left of ;/: is the head and the right the body

    # alternatively we search for these key words (this is a weakness of the solution right now because of the reliance on specific words)
    m = re.match(
        r'^\s*((?:[Aa]n?\s+|[Tt]he\s+).{0,400}?\b(?:compris\w*|includ\w*|consist(?:s|ing)?\s+of))\b[ ,:]+(.*)$',
        text, flags=re.S
    )
    if m: #we then treat everything to the left of the word as the head and the right as the body
        return m.group(1).strip(' ,.'), m.group(2).lstrip(' ,.')

    #worst case we call the engine by default and assign the first sentence as the head *******
    doc = nlp(text)
    sents = list(doc.sents)
    if sents:
        first = sents[0].text
        return first.strip(' ,.'), text[len(first):].lstrip(' ,.')

    return text.strip(' ,.'), ""


APPOSITIVE_SPLIT_RE = re.compile(r",\s+(?=(?:the|a|an)\b)", re.I) #these are the primary candidates to split on for each new NP
AND_DET_SPLIT_RE = re.compile(r",\s+and\s+(?=(?:the|a|an)\b)", re.I)

def is_np_like(text, nlp):
    doc = nlp(text)
    for t in doc:
        if t.pos_ in VERBISH_POS and "Fin" in t.morph.get("VerbForm"): #two checks on the spacy generated token: 1. is it a verbish pos
            return False # and is it finite (as in past tense conjugated) and we return false because this isnt NP-like meaning we have a
    return True # full clause

def safe_np_split(text, regex, nlp):
    #split up text based on given regex rule
    raw_parts = regex.split(text)
    #clean up input
    parts = []
    for p in raw_parts:
        if p and p.strip(" ,."):
            parts.append(p.strip(" ,."))

    #if there arent enough parts then just return the whole thing
    if len(parts) <= 1:
        return [text.strip(" ,.")]

    #we only return if all the pieces are NP-like, otherwise return the text
    for piece in parts:
        if not is_np_like(piece, nlp):
            return [text.strip(" ,.")]
    return parts

def split_requirements(body, nlp):
    if not body: return [] #return on blank input
    primaries = split_top_level_semicolons(body) or [body] #returns based on semicolon splits or just takes the body
    out = []
    for r in primaries:
        for p in safe_np_split(r, AND_DET_SPLIT_RE, nlp): #we split based on and_det
            pieces = safe_np_split(p, APPOSITIVE_SPLIT_RE, nlp) #
            for piece in pieces:
                out.append(piece)
    cleaned = []
    for t in out:
        x = t.strip(" ,.")  # remove leading/trailing spaces, commas, periods
        if x:  # only keep if not empty string
            cleaned.append(x)

    return cleaned

def findBounds(tok):
    # find the leftmost edge
    start_index = tok.left_edge.i

    # Find the rightmost edge
    rightmost_index = None
    for t in tok.subtree:
        if rightmost_index is None or t.i > rightmost_index:
            rightmost_index = t.i

    # return as a (start, end) tuple
    return (start_index, rightmost_index)


def extract_subrequirements(req_text, nlp):
    doc = nlp(req_text) #use nlp engine on text
    cand = []

    # here we check to see if the token dependency label is that of a clause dependency which makes it likely
    # candidate so we add
    for tok in doc:
        if tok.dep_ in CLAUSE_DEPS:
            cand.append(findBounds(tok))

    # search for the pattern "to +VERB" and take its subtree as a candidate
    for i, tok in enumerate(doc):
        if tok.lower_ == "to" and i+1 < len(doc) and doc[i+1].pos_ in VERBISH_POS:
            cand.append(findBounds(tok))

    # what we think are contentful prepositional prases (preposition + object of interest + modifiers)
    # also note that a preposition relates an object to anoter
    for tok in doc:
        if tok.dep_ == "prep": #preposition phrase check using spacy
            s, e = findBounds(tok) #get the begniing and end of the subtree
            span = doc[s:e+1]
            content = []  # start empty list
            for t in span:  # iterate over every token in the span
                if t.pos_ in CONTENT_POS:  # check if its POS is contentful
                    content.append(t) #append if so
            if len(span) >= 5 and len(content) >= 2: #we also duble check that there are at least two content tokens and it isnt too small
                cand.append((s, e)) #if all is well, then append!
    # deduplication and sorting, keeping only spans not in another span
    cand = sorted(set(cand), key=lambda se: (se[0], -(se[1]-se[0])))
    kept = []
    for s, e in cand:
        if not any(s >= ks and e <= ke for ks, ke in kept):
            kept.append((s, e))

    # check inside each kept span
    split_spans = []
    for s, e in kept:
        span = doc[s:e+1]
        local = []
        for t in span:
            for c in t.children:
                if c.dep_ == "conj": # we are looking for any coordinating conjunctions
                    cs, ce = findBounds(c)
                    if s <= cs <= ce <= e:
                        local.append((cs, ce)) #split into the clause before and after the CC^
        split_spans.extend(local or [(s, e)])#if unfound, keep the span as a whole item

    # just filtering out non-valid sets that make it thru
    out, seen = [], set()
    for s, e in sorted(set(split_spans), key=lambda se: se[0]):
        span = doc[s:e+1]
        if len(span) < 3: continue #too short check
        func = sum(1 for t in span if t.pos_ in {"ADP","DET","PRON","PART","PUNCT","CCONJ","SCONJ"})
        if func / len(span) > 0.6: continue #too wordy check, we check if there is >60% of determiners, PP, punc, etc
        text = span.text.strip(" ,.;")
        base = set(w.lower() for w in re.findall(r"\w+", req_text))
        here = set(w.lower() for w in re.findall(r"\w+", text))
        if here and len(here & base) / len(here) >= 0.8: continue #too much overlap check
        if text not in seen:
            seen.add(text); out.append(text)
    return out #returns cleaned up string


def split_wherein(req): #just splits on wherein clauses
    parts = re.split(r"\bwherein\b", req, flags=re.I) #splits on wherein with regex
    if len(parts) > 1: #if there is more than one part
        head = parts[0].strip(" ,.") #assign the first part as te head
        tails = ["wherein " + p.strip(" ,.") for p in parts[1:] if p.strip()] #assign the rest as te tail
        return head, tails #return head+wherein clauses
    return req, [] #just return an empty list of tails

def split_tail_after_colon_as_subs(text):
    i = text.find(':') #find the first colon
    if i == -1 or i == len(text) - 1: #make sure someting exists after the colon
        return [] #otherwise return empty list
    tail = text[i+1:].strip() #take the stuff after the colon
    pieces = []
    for p in split_top_level_semicolons(tail): #get the main subjects from the tail
        if p:  # only keep non-empty strings
            pieces.append(p)
    if pieces:
        return pieces
    else:
        return [tail] #return either pieces or tail depending on if there are valid pieces


def rethread_requirements(req_texts, nlp):
    pairs = []
    def root_tag(s):
        d = nlp(s)
        for t in d:
            if t.dep_ == "ROOT": return t.tag_ #get the tag of the word
        return "" #otherwise return a blank string
    for r in req_texts:
        r = r.strip()
        if not r: continue #look at the input texts and if there isnt anything then skip
        if re.match(r'^\s*wherein\b', r, flags=re.I): #lines starting with wherein become their own main
            pairs.append([r, []]); continue
        if pairs and pairs[-1][0].rstrip().endswith(':') and is_np_like(r, nlp): #if the previous main
            pairs[-1][1].append(r); continue #ended wit : and the current text is NP-like then attach to the previous
        if pairs and is_np_like(r, nlp) and root_tag(pairs[-1][0]).upper() == "VBG": #if the previous main root tag is VBG
            pairs[-1][1].append(r); continue #and current is NP-like, then attach as a child
        pairs.append([r, []])
    result = []
    for item in pairs:
        m = item[0]  # main string
        subs = item[1]  # list of children
        result.append((m, subs))  # add as a tuple
    return result #return the tuple


def _chunks_by_commas_with_verbs(tail_doc):
    chunks, buf = [], [] #gets chunks and the buffer list
    def flush():
        s = "".join(buf).strip(" ,.;") #join together all the elements in buffer
        if s: chunks.append(s) #assuming there is content after being cleared, append to chunks list
    i = 0
    while i < len(tail_doc):#goes over the input tokens
        tok = tail_doc[i]
        starts_verbish = (
            tok.pos_ in VERBISH_POS
            or (tok.lower_ == "to" and i+1 < len(tail_doc) and tail_doc[i+1].pos_ in VERBISH_POS)
            or tok.tag_ == "VBG"
        ) #we check if the pos is in the verbish pos list, we check for infinitives ("to" do something), and we make sure we can get participle conjugations as well
        if starts_verbish and buf: #assuming verbish and there is a non-empty buffer
            prev = tail_doc[i-1] if i>0 else None #we assign prev to be the chunk before curr
            if prev and (prev.text == ',' or prev.lower_ == 'and'): #we are looking to make sure before it there was a , or and meaning this is a new chunk
                flush(); #flush old buf as one chunk
                buf = []; #clear buf
        buf.append(tok.text_with_ws); i += 1 #add token text to buffer
    flush() #whatever is left is assigned to buf
    return chunks #return the list of combined cunks

def decompose_actions(text, nlp):
    doc = nlp(text) #run nlp
    if not list(doc): return [text] #if theres noting then just return the input

    colon_i = None
    for i, t in enumerate(doc): #we get index, token
        if t.text == ':': #we check if the token is a colon
            colon_i = i #colon index
            break
    if colon_i is not None and 0 < colon_i < len(doc)-1: #find first colon that isnt at either index:0 or doc len -1
        parent = doc[:colon_i].text.strip(" ,.;") #we assign parent to text before the colon
        tail_doc = nlp(doc[colon_i+1:].text) #we run model on the stuff after the colon
        chunks = _chunks_by_commas_with_verbs(tail_doc) #and call earlier chunker to break things up better
        if len(chunks) >= 2: #length sanity check
            return [parent + ":"] + chunks #return the parent + content chunks

    # else we look toward verb heads
    roots = []
    for t in doc:
        if t.dep_ == "ROOT" and t.pos_ in VERBISH_POS: roots.append(t) # if we find a ROOT that is also a verbish pos then append to roots
    for t in doc:
        if t.pos_ in VERBISH_POS and t.dep_ in {"conj","xcomp","ccomp","parataxis"}: roots.append(t) #also same thing but with conjunctions,
    if not roots: return [text] #open clausual complement, clasual complement, and loosely attached/side-by-side clauses

    #collect spans from each verb head
    spans_list = []
    for h in roots:
        span = findBounds(h)  # returns tart_index, end_index
        spans_list.append(span)

    # convert to set, then back to list to dedupe
    unique_spans = set(spans_list)

    # sorted by start index first
    spans = sorted(unique_spans, key=lambda se: (se[0], se[1]))
    kept = []
    for s,e in spans:
        inside_any = False
        for ks, ke in kept:  # loop over all previously kept spans
            if s >= ks and e <= ke:  # if current span [s,e] inside [ks,ke]
                inside_any = True
                break  # we are done

        if not inside_any: #we append the content that isn't there already
            kept.append((s,e))

    out = [] #final output filtering
    for s,e in kept:
        span = doc[s:e+1]
        content = []
        for t in span: #we get the content pos and if its in our list then we append it to the ouput
            if t.pos_ in CONTENT_POS:
                content.append(t)
        if len(content) >= 2:
            out.append(span.text.strip(" ,.;")) #if there are more than two blocks then add te span with formatting
    if len(out) >= 2:
        return out #return out if there is a reasonable amount of content
    else:
        return [text]



def render_outline(head, reqs_with_grouped, nlp):
    print("\n— CLAIM OUTLINE —")
    print(f"Head/Preamble: {head}")
    print("Requirements:") #preemtive outline strucutrue at the top
    for i, (req, subs) in enumerate(reqs_with_grouped, 1): #go through the (requirement, subclasses) tuple
        print(f"  {i:02d}. {req}") #assigned a two digit number
        sub_idx = 0 #tracks the subclasses
        for s in subs: #looking at the subclasses now
            # split 'wherein' first, then get actions inside each piece
            grouped = [(s, [])]
            grouped = split_internal_whereins(grouped) #breka down each clause on wherein
            for (piece, _kids) in grouped:
                parts = decompose_actions(piece, nlp) #further decomposition of each piece
                if parts and parts[0].rstrip().endswith(":"): #if the first part ends with a colon, this is a paretn
                    parent = parts[0].rstrip(" :")
                    sub_idx += 1 #iterates the id
                    print(f"      {i}.{sub_idx} {parent}:") #for here
                    for j, child in enumerate(parts[1:], 1):
                        print(f"          {i}.{sub_idx}.{j} {child}") #print in the 1.->1.1 format
                elif len(parts) > 1:#if we have multiple chunks from decompose_actions
                    for p in parts:
                        sub_idx += 1
                        print(f"      {i}.{sub_idx} {p}") #we get a subid too
                else:
                    sub_idx += 1
                    print(f"      {i}.{sub_idx} {parts[0] if parts else piece}")# if there is only one part, print as a single numbered subclause

# minimalist internal-wherein splitter used by renderer
def split_internal_whereins(grouped):
    out: List[Tuple[str, List[str]]] = []
    for head, kids in grouped: #remember our subject, requirment tuple
        parts = re.split(r"\bwherein\b", head, flags=re.I) #for each tuple, split on the wherein command
        if len(parts) <= 2: #if there is only 1 wherein, then skip further splits
            out.append((head, kids)); continue
        pre = parts[0].strip(" ,.") #strip punc
        if pre: #as long as non-empty, reattac to output list
            out.append((pre, kids))
            kids = [] #reset the kids list so it doenst mess up the new iteration
        for p in parts[1:]:
            seg = "wherein " + p.strip(" ,.") #reattach the wherein
            out.append((seg, [])) #appended with empty kids
    return out #return

# ---------- main ----------
if __name__ == "__main__":
    # Put any claim text here to test
    TEXT = (
        # "A conductor shaping apparatus that shapes at least one first bent portion and at least one second bent portion "
        # "of a conductor that is bent in a first bend axis and a second bend axis that is orthogonal to the first bend axis, "
        # "respectively, the conductor shaping apparatus comprising first and second shaping dies that are movable toward and away "
        # "from each other along a first axis, and that are moved toward each other to shape the at least one first bent portion "
        # "and the at least one second bent portion, wherein one of the first and second shaping dies is configured to be moved away "
        # "from the other along a second axis that is different from the first axis such that the conductor is not dragged when the "
        # "first and second shaping dies are moved away from each other along the first axis after shaping of the first and second "
        # "bent portions is completed, wherein, the first and second shaping dies are configured such that: the first and second "
        # "shaping dies approach each other along the first axis until the conductor abuts a first bending portion pressing surface of "
        # "the second shaping die, the first and second shaping dies thereafter approach each other along the second axis until the "
        # "conductor abuts a second bending portion pressing surface of the second shaping die, the first and second shaping dies "
        # "thereafter approach along only the first axis to form the first and second bent portions, and the first and second shaping "
        # "dies are moved away from each along only the second axis after shaping is complete."
        # " A nanoscale device comprising an elongated crystalline semiconductor nanostructure having a plurality of substantially plane side facets, and a first facet layer of a superconductor material covering at least a part of one or more of said side facets, wherein the interface between the at least one facet of the elongated crystalline semiconductor nanostructure and the first facet layer is configured to induce a superconductor hard gap in the semiconductor nanostructure."
        # "A system for managing a conference meeting, the system comprising: an electronic data store; and one or more computer hardware processors in communication with the electronic data store, the one or more computer hardware processors configured to execute computerexecutable instructions to at least: receive a first audio signal from a first voice-enabled device; identify a first user profile based on the first audio signal, wherein identifying the first user profile comprises performing speaker recognition on the first audio signal and using a first user voice profile; receive a second audio signal from a second voice-enabled device; identify the first user voice profile from the second audio signal; generate a group of voice-enabled devices based on identifying the first user voice profile from both the first audio signal and the second audio signal, wherein the group comprises the first voiceenabled device and the second voice-enabled device, wherein the first voice-enabled device and the second voice-enabled device are in different rooms, wherein voice input from a conference call participant is received by the first voice-enabled device and the second voice-enabled device, and wherein the first voice-enabled device is associated with a first account different than a second account associated with the second voice enabled device; receive a third audio signal from the first voice-enabled device; identify a voice command from the third audio signal; determine, using the group, that the voice command was also received by the second voice-enabled device; determine that the voice command corresponds to a command to leave a conference call associated with a meeting; identify a first user profile based on the third audio signal, wherein identifying the first user profile comprises identifying the first user voice profile from the third audio signal; identify an association between the first user profile and the first voice-enabled device; select the first voice enabled device, from the first voice-enabled device and the second voice enabled device, based on the association between the first user profile and the first voice-enabled device; and execute the voice command, wherein execution of the first voice command causes the first voice enabled device to disconnect from the conference call."
        # " A method for execution by one or more processing modules of one or more computing devices of a dispersed storage network (DSN), the method comprises: receiving and storing data; receiving a corresponding task(s) to be executed on the stored data; selecting a number of distributed storage and task execution (DST EX) units to favorably execute partial tasks of the corresponding task(s), wherein the partial tasks are processed in parallel to complete an overall task within a desired task execution time period; determining task partitioning based on one or more of distributed computing capabilities of the selected DST EX units; determining processing parameters of the data based on the task partitioning; partitioning the task(s) based on the task partitioning to produce the partial tasks; processing the data in accordance with the processing parameters to produce slice groupings, wherein the slice groupings include groups of encoded data slices; and sending the slice groupings and corresponding partial tasks to the DST EX units in accordance with a pillar mapping."
        # " An apparatus for carbon dioxide gas separation, comprising a gas source, a flow distributor, a gas flow meter, a venturi jet unit provided with two liquid inhaling inlets, a tubular hydrate reaction unit, a gasliquid-solid three-phase separation unit, a first slurry pump, a hydrate dissociation unit provided with a first pressure maintaining valve at its top, a second slurry pump, and a solution saturation tank provided with a third safety valve at its top, which are communicated sequentially, further comprising a chemical absorption tower, a second corrosionresistant pump, a heat exchanger, a regeneration tower, a third corrosion-resistant pump, and a reservoir containing a CO 2 chemical absorbent, which are communicated sequentially, wherein, the reservoir is communicated with an upper portion of the chemical absorption tower through a first corrosion-resistant pump to form a cycle; the flow distributor is communicated with a bottom inlet of the solution saturation tank, and a bottom outlet of the solution saturation tank is communicated with the two liquid inhaling inlets of the venturi jet unit through sequentially a liquid-phase mass flow meter and a ninth stop valve; a second safety valve is disposed at a top of the gas-liquid-solid three-phase separation unit; the gas-liquid-solid three-phase separation unit is communicated with a lower portion of the chemical absorption tower through sequentially a third one-way gas valve, a second pressure maintaining valve and a fourth one-way gas valve; an upper portion of the chemical absorption tower is communicated with a hydrogen collecting tank provided with a first safety valve through a fifth one-way gas valve; the regeneration tower is further communicated with the hydrate dissociation unit, and regenerated carbon dioxide gas is directed to the hydrate dissociation unit in which it will be mixed with the carbon dioxide produced during the dissociation and then subjected to a subsequent processing."
        " A child motion apparatus comprising: a base frame assembly for providing standing support on a floor; a column connected with the base frame assembly; a support arm extending generally horizontally relative to the column, the support arm having a first and a second end portion, the first end portion being assembled with the column and having a channel extending generally vertically, the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; a child seat connected with the second end portion of the support arm; a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm."
    )

    nlp = spacy.load("en_core_web_sm")

    head, body = detect_head(TEXT, nlp)
    req_texts = split_requirements(body, nlp)
    main_with_presubs = rethread_requirements(req_texts, nlp)

    # (top level, requirements)
    req_with_subs: List[Tuple[str, List[str]]] = []

    for main, pre_subs in main_with_presubs:
        # get stuff after colon as colontail
        colon_tail = split_tail_after_colon_as_subs(main)

        #normalize the main head
        if ':' in main:
            main_head = main.split(':', 1)[0].strip(" ,.")
        else:
            main_head = main

        # split off initial wherein
        head_only, wh_from_main = split_wherein(main_head)

        # extra subrequirements from the head
        structural = extract_subrequirements(head_only, nlp)

        # add all up: from colon tail,any preexisting subs attached upstream (pre_subs)
        # wherein pulled out of the head, structural subclauses found by NLP
        flat_subs = []
        flat_subs.extend(colon_tail)
        flat_subs.extend(pre_subs)
        flat_subs.extend(wh_from_main)
        flat_subs.extend(structural)

        # deduplicate
        seen = set()
        deduped = []
        for s in flat_subs:
            if s not in seen:
                deduped.append(s)
                seen.add(s)
        flat_subs = deduped

        #store clean with subclasses
        req_with_subs.append((head_only, flat_subs))

    render_outline(head, req_with_subs, nlp)
