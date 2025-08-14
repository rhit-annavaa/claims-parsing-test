from __future__ import annotations
import re

#these are the identifiers we will search through with regex, the list can be added onto
NUM_RX = re.compile(r'(?m)^\s*(\d+)\.\s') #claims with numbers
PRIORITY_OPENERS = re.compile(r'\b(comprising|including|consisting of|consisting essentially of)\b', re.I) #opener keywords that usually split the preamble from the main body
OPENERS = re.compile(r'\b(comprising|including|consisting of|consisting essentially of|having|containing|characterized in that|features)\b', re.I) #secondary openers that are deffered to if no primary openers exist
INNER_OPENER = re.compile(r'\b(comprising|including|consisting of|consisting essentially of|having|containing|characterized in that|features)\b\s*:?', re.I) #generally looking for openers where we are already inside a top level claim
WHEREIN = re.compile(r'\b(wherein|whereby)\b', re.I) #wherein clauses
DEPEND_RX = re.compile(r'\bof\s+claims?\s+([\d,\-\u2013\u2014\s]+)\b', re.I) #captures numbers for claims

#standardize the text here
def normalize(text):
    text = text.replace("\u2013", "-").replace("\u2014", "-") #dashes handling
    text = re.sub(r'\s+', ' ', text) #whitepsace collapse
    text = re.sub(r'\s*([;:,])\s*', r'\1 ', text) #tighten spacing around punctuation
    # text = re.sub(r'\belectrically\s*conductive\b', 'electrically-conductive', text, flags=re.I) #short term fix
    return text.strip()

#
# def split_into_claims(text): #this looks for numerical claims and attempts to seperate them
#     t = re.sub(r'\n+', '\n', text.strip())
#     positions = []
#     for m in NUM_RX.finditer(t):
#         start_index = m.start()  # index in string t where the match begins
#         claim_number_str = m.group(1)  # first capture group from the regex (the digits)
#         claim_number = int(claim_number_str)  # convert from string to integer
#         positions.append((start_index, claim_number))
#     if not positions:
#         return [(1, normalize(text))]
#     out = []
#     for i, (pos, cid) in enumerate(positions):
#         end = positions[i+1][0] if i+1 < len(positions) else len(t)
#         chunk = t[pos:end]
#         chunk = re.sub(r'^\s*\d+\.\s*', '', chunk).strip()
#         out.append((cid, normalize(chunk)))
#     return out

#
# def parse_depends(text): #
#     m = DEPEND_RX.search(text)
#     if not m: return None #searches for parent claims using specific identifying words, returns none if not found
#     raw = m.group(1).replace(" ", "") #take the captured parent claims and strip space out
#     ids = []
#     for part in raw.split(","): #split on commas
#         if "-" in part:
#             a,b = part.split("-",1)
#             if a.isdigit() and b.isdigit():
#                 a,b = int(a), int(b)
#                 ids.extend(range(min(a,b), max(a,b)+1))
#         elif part.isdigit():
#             ids.append(int(part))
#     return ids or None

#grab and seperate body and preamble
def extract_preamble_and_subject(claim_text):
    m = PRIORITY_OPENERS.search(claim_text)
    if not m:
        m = OPENERS.search(claim_text) #find opener words first
    if not m: #look for the specific pattern of An/A/The + a cue word like for/configured/etc
        m2 = re.search(
            r'^\s*((?:An?|The)\s+[A-Za-z][\w\s\-]*?)'
            r'(?=\s+(for|configured|having|including|comprising)\b|,|\.)',
            claim_text,
            flags=re.I
        )

        # If we find the pattern, we will clean the percieved root
        if m2:
            root = m2.group(1).strip(" ,.")
        else:
            root = None

        # return as preamble, body
        return (claim_text, root, "")

    # Alternatively, if we find an opener off rip
    match_start_index = m.start() #we find the start of body

    preamble_portion = claim_text[:match_start_index] #grab the preamble

    preamble_cleaned = preamble_portion.strip(" ,.") #clean the preamble

    preamble = preamble_cleaned

    # The rest is everything after the opener.
    match_end_index = m.end()

    rest_portion = claim_text[match_end_index:] #get everything after the preamble

    # clean-up
    rest_cleaned = rest_portion.strip(" ,.")

    #body
    rest = rest_cleaned

    #get the root out of the preamble, this is very much not working well yet
    mlead = re.match(
        r'^\s*((?:An?|The)\s+[A-Za-z][\w\s\-]*?)\b',
        preamble,
        flags=re.I
    )
    if mlead:
        root_subject = mlead.group(1).strip(" ,.")
    else:
        root_subject = None

    # last 6 words fallback if we can't find the subject
    if not root_subject:
        tokens = preamble.split()
        root_subject = " ".join(tokens[-6:]).strip(",. ") or None

    #remove in which from the
    # preamble = re.sub(r'\bin which\b', '', preamble, flags=re.I).strip(" ,.")

    # return cleaned up pieces
    return (preamble, root_subject, rest)

#these are essentially helper methods that can help partition up the text
def split_semicolons_outside_parens(s):
    parts = [] #for the final
    buf = [] #buffer for characters in curr segment
    dp = 0 #counts depth of parenthesis
    db = 0 #counts depth of brakcets
    dc = 0 #counts depth of curly braces
    for ch in s: #go thru each char in the string
        if ch == '(': dp += 1 #increase or decrease the count for each [],(),{} incrementing and decrementing where necessary
        elif ch == ')': dp = max(0, dp-1) #note: we use max(0,dp-1) because we dont want a negative number
        elif ch == '[': db += 1
        elif ch == ']': db = max(0, db-1)
        elif ch == '{': dc += 1
        elif ch == '}': dc = max(0, dc-1)
        if ch == ';' and dp==db==dc==0: #once we get to a semicolon and we are outside of any parenthesis, then we can split
            seg = "".join(buf).strip(" ,.:")
            if seg: parts.append(seg)
            buf = [] #this just saves the current segment and appends it to parts and then clears the buffer
        else:
            buf.append(ch) #if not keep splitting
    tail = "".join(buf).strip(" ,.:")
    if tail: parts.append(tail)
    return parts #following the loop, ensures the stuff after the last break gets included

def split_top_level_elements(rest):
    # return empty list if there is no input
    if not rest:
        return []

    # call to split on semicolons
    raw_parts = split_semicolons_outside_parens(rest)

    #get rid of empty strings
    parts = []
    for p in raw_parts:
        if p:  # keep only non-empty strings
            parts.append(p)

    #strip out and, ors
    cleaned = []
    for p in parts:
        # Remove a leading "and " or "or " if present
        without_lead_conj = re.sub(r'^(and|or)\s+', '', p, flags=re.I)
        cleaned.append(without_lead_conj)

    #return main subjects
    return cleaned

def flush_buffer(buf, parts):#gets rid of
    seg = "".join(buf).strip(" ,.:") #buffer content
    if seg: #if the list isnt empty
        parts.append(seg)
    final = [] , parts
    return final #return empty list + parts

def split_commas_coord_outside_parens(s):
    parts = []  # for the final
    buf = []  # buffer for characters in curr segment
    dp = 0  # counts depth of parenthesis
    db = 0  # counts depth of brakcets
    dc = 0  # counts depth of curly braces
    i = 0

    while i < len(s):
        ch = s[i]
        if ch == '(': dp += 1
        elif ch == ')': dp = max(0, dp-1)
        elif ch == '[': db += 1
        elif ch == ']': db = max(0, db-1)
        elif ch == '{': dc += 1
        elif ch == '}': dc = max(0, dc-1) #same thing as above, we increment or decrease based on opening and closing brackets

        if dp == db == dc == 0: #if we are outside brackets, then we look
            if s[i:i+6].lower() == ", and ": #look 6 chars ahead for an "and" becase ", and " <-6 characters
                buf, parts = flush_buffer(buf, parts)
                i += 6
                continue
            if s[i:i+5].lower() == ", or ": #same thing here, look for "or" because ", or " <-5 char
                buf, parts = flush_buffer(buf, parts)
                i += 5
                continue
            for kw in (" and having ", " and including ", " and containing ", " and comprising "): #longer coordinating prases to think of
                L = len(kw) #number of chars to skip
                if s[i:i+L].lower() == kw: #find a match
                    buf, parts = flush_buffer(buf, parts) #flush
                    i += L #jump past phrase
                    continue

        buf.append(ch)
        i += 1

    # Flush the last segment
    buf, parts = flush_buffer(buf, parts)

    return parts


def split_first_second_clauses(s): #looks for the "first ____, the second ___" pattern
    m1 = re.search(r'\bthe\s+first\b', s, flags=re.I) #we confirm that "the first" exists
    m2 = re.search(r'\bthe\s+second\b', s, flags=re.I) #we confirm that "the second" exists
    if not (m1 and m2):
        return [s] #just return original string if these don't both exist

    parts = [] #final list of segments
    dp = 0 #depth counter for parentheses
    db = 0 #depth counter for brackets
    dc = 0 #depth counter for curly braces
    split_idx = None #index where we split on ", the second"

    #loop over every character with its index
    for i, ch in enumerate(s): #enumerate gives each entry a id
        if ch == '(': dp += 1
        elif ch == ')': dp = max(0, dp - 1)
        elif ch == '[': db += 1
        elif ch == ']': db = max(0, db - 1)
        elif ch == '{': dc += 1
        elif ch == '}': dc = max(0, dc - 1) #increment or decrement depth counters depending on bracket type
        #check if we are outside brackets
        if dp == 0 and db == 0 and dc == 0:
            #check for the  string ", the second" starting here
            if s[i:i + 12].lower() == ", the second":
                split_idx = i
                break #stop after finding a match

    #return original if no split
    if split_idx is None:
        return [s]

    #start index of "the second..." text skipping 3 spaces for ", "
    sec_start = split_idx + 3

    #look for identifiers like ", wherein" or ";" in the text after "the second"
    tail_after_second = s[sec_start:]
    m_wherein = re.search(r',\s*wherein\b', tail_after_second, flags=re.I)
    m_semicolon = re.search(r';', tail_after_second)

    #determine when the clause ends
    boundary = len(s)
    if m_wherein:
        boundary = min(boundary, sec_start + m_wherein.start())
    if m_semicolon:
        boundary = min(boundary, sec_start + m_semicolon.start())

    #check if the "second ..." section before the boundary contains an of these seperating verbs
    looks_like_clause = re.search(
        r'\b(is|are|being|configured|coupled|connected|disposed|comprises|includes)\b',
        s[sec_start:boundary],
        flags=re.I
    )
    if not looks_like_clause:
        return [s] #don't split if the right-hand side isn't a full independent clause/subclause

    #split into left/right parts, strip punctuation/whitespace
    left = s[:split_idx].strip(" ,.:")
    right = s[split_idx + 1:].strip(" ,.:")

    #only return split if both sides are non-empty
    if left and right:
        return [left, right]
    return [s]


#build the struct
def make_node(text, kind="limitation", children=None): #we make a node tuple
    return (text, kind, children or []) #creates an empty list for a child

def parse_element_recursive(text): #get one element into the tree using recursion
    text = text.strip(" ,.") #clean up leading and trailing spaces
    if not text: return make_node("") #if empty then make an empty node
    m_where = WHEREIN.search(text) #searches for wherein statements
    if m_where:
        before = text[:m_where.start()].strip(" ,.")  # stuff before wherein
        where_tail = text[m_where.end():].strip(" ,.")  # stuff after wherein
    else:
        before = text  # no wherein, so all text is "before"
        where_tail = None #no tail

        # inner-subclause opener search
    m_open = INNER_OPENER.search(before)
    if not m_open:#make a leaf if there is no inner opening
        node = make_node(before)
    else:
        # split the before "wherein" term around the inner opener into head (parent) and tail (list block)
        head = before[:m_open.start()].strip(" ,.")  # the parent text
        tail = before[m_open.end():].strip(" ,.")  # the list text after opener

        # create the parent node; use head if available, otherwise "before"
        if head:
            node = make_node(head)
        else:
            node = make_node(before)

        #first split by top-level semicolons
        result = split_top_level_elements(tail)
        if result:
            chunks = result
        else:
            chunks = [tail]
        #split each chunk by top-level comma patterns
        subitems = []
        for ch in chunks:
            pieces = split_commas_coord_outside_parens(ch) or [ch]
            subitems.extend(pieces)

        # recurse on sub-subjects and attach nodes as children
        for sub in subitems:
            if sub:
                _text, _kind, kids = node  # unpack to get the children list reference
                kids.append(parse_element_recursive(sub))

    # wherein tail handling
    if m_where and where_tail:
        # split the wherein tail by top-level semicolons first
        wherein_blocks = split_top_level_elements(where_tail) or [where_tail]

        for w in wherein_blocks:
            # handle patterns like "the first ..., the second ..." inside wherein blocks
            pieces = split_first_second_clauses(w)
            for piece in pieces:
                wn = parse_element_recursive(piece)  # recurse as usual
                wn = (wn[0], "wherein", wn[2])  # tag the node as "wherein"
                node[2].append(wn)  # append under current node

    return node

def build_elements(rest): #builds the top-level elements
    prelim = [] #return list

    # split top-level pieces via semicolons
    for p in split_top_level_elements(rest): #we split at top-level ';'
        n = parse_element_recursive(p) #parse each p into a (text, kind, children) node

        # if the node has no text but has children, elevate child to top-level
        if (not n[0] or n[0].strip() == "") and n[2]:
            prelim.extend(n[2]) #append its children directly
        else:
            prelim.append(n) #keep the node as-is

    return prelim


# parse
def parse_and_render(raw):
    # checks if raw is a str
    if isinstance(raw, str):
        claims = [normalize(raw)] if raw.strip() else []#else assume there are plural strs
    else:
        # list of str
        claims = []
        for c in raw:
            if isinstance(c, str) and c.strip():
                claims.append(normalize(c))

    out_blocks = []
    for text in claims:
        # parents = parse_depends(text)
        # parents = text
        parents = None
        # ctype = "dependent" if parents else "independent"
        ctype = "independent"
        preamble, root_subject, rest = extract_preamble_and_subject(text)

        if rest: #build elements from body
            elements = build_elements(rest)
        else: #fallback
            m = WHEREIN.search(text) #or build elements from a trailing wherein
            if m: #if we find then build based on pattern
                tail = text[m.end():].strip(" ,.")
                tmp = [parse_element_recursive(p) for p in split_top_level_elements(tail) or [tail]]
                elements = []
                for n in tmp:
                    if (not n[0] or n[0].strip()=="") and n[2]:
                        elements.extend(n[2])
                    else:
                        elements.append(n)
            else: #otherwise return nothing
                elements = []

            # render lines
        lines = []
        dep_note = ""  #
        lines.append(f"Claim ({ctype}{dep_note})")  #append claim
        topic = (root_subject or preamble or "—").strip()
        lines.append(f"Preamble: {topic}") #get the first word (still in progress)
        lines.append("Requirements:")

        def bullet(text, level=0, tag="•"):#text to display, depth in heirarchy, tag for type of bullet
            indent = "  " * level #two spaces per levle
            lines.append(f"{indent}{tag} {text.strip()}") #appends formatted string to lines

        def walk(nodes, level=1): #
            for t,k,chs in nodes: #loops through nodes
                bullet(t, level, "•") #calls bullet to get the main claims
                for ch in chs: #print child tags if applicable
                    tag = "↳ (wherein)" if ch[1]=="wherein" else "↳"
                    bullet(ch[0], level+1, tag)
                    if ch[2]: #if there is a childs child,
                        walk(ch[2], level+2)

        if elements: #start walking at the first level if there are elemtsn
            walk(elements, 1)
        else: #otherwise there arent any requirements so "-"
            lines.append("  —")
        out_blocks.append("\n".join(lines)) #lines becomes a single block and

    return "\n".join(out_blocks) #returns


if __name__ == "__main__":
    raw = """
 A child motion apparatus comprising: a base frame assembly for providing standing support on a floor; a column connected with the base frame assembly; a support arm extending generally horizontally relative to the column, the support arm having a first and a second end portion, the first end portion being assembled with the column and having a channel extending generally vertically, the support arm further being connected with the column via a hinge about which the support arm is rotatable generally horizontally relative to the column; a child seat connected with the second end portion of the support arm; a vertical actuating mechanism supported by the base frame assembly and operable to drive the column to slide upward and downward relative to the base frame assembly; and a horizontal actuating mechanism operable to drive the support arm to oscillate generally horizontally relative to the column, the horizontal actuating mechanism including a driving part movable along a circular path and guided for sliding movement along the channel at the first end portion of the support arm, wherein a circular motion of the driving part causes the driving part to slide along the channel and thereby drives an oscillating movement of the support arm.
 """
print(parse_and_render(raw))
    