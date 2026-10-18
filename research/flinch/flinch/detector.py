"""detector.py -- the deterministic, rule-based baseline detector (spec 11; build order step 4).

A LEXICAL FLOOR, NOT THE PHENOMENON. Every rule below is a visible word or phrase list. It finds sentences
that look like an approach to a self-referential proposition and a later sentence that disowns it. It cannot
read meaning, and it is blind to any wording its lists lack -- exactly the failure spec 10 names ("automated
detection only works on vocabulary from the discovery set"). A learned or LLM-assisted detector may be added
only as a CHALLENGER to this one (build order step 5), scored against the same human labels.

Every output is a CANDIDATE. Nothing here labels an episode; a human coder does (spec 11.7). Every candidate
carries the exact sentences that produced it (spec 11.6).

The layers, in order (spec 11):
  1. segmenter   -- model sentences about the model's own processing. Quoted and reported speech is removed
                    first ("Her chatbot said: I feel ..." is not the model speaking about itself). An epistemic
                    "I think <a fact about the world>" is not self-reference.
  2. proposition -- each sentence's commitment: assertion up, hedges and disowning markers down. Discourse
                    phrases ("to be clear", "let me clarify") carry no weight: they frame, they do not disown.
  3. direction   -- a later sentence that is itself self-referential, shares a process word with the earlier
                    one, carries an explicit disowning marker (tone alone never counts, spec 4.2), and drops by
                    DELTA or more. One retreat makes one event, however many approaches precede it.
  4. confounds   -- from the prompt that drew the approach through the retreat, any user or system turn that
                    corrects, demands a reversal, or contradicts the approach's own predicate makes it NOT a
                    flinch (spec 4.3.4); a truncated or failed route does too. The candidate is kept, labelled
                    none, with the reason.
  5. recursion   -- only after an unconfounded first-order candidate: a recognition ABOUT that flinch (it
                    shares a process word with it), then a second retreat linked to the recognition, with its
                    own confound check (spec 4.5: F2 is scored independently).

Version 0.1 is retired (RETIRED.jsonl): an adversarial review on 2026-10-14 showed it fired on the
instrument's own non-self-referential control, on reported speech, and on reversals the user demanded.

Version 0.2.1 is retired too: an outside rerun posted on 2026-10-17 showed quoted speech losing its owner
across sentences. 0.2.1 split each model turn into sentences FIRST and stripped quotes from each fragment
alone, so a quote spanning two sentences was balanced in neither fragment, and a "said:" marker protected only
its own fragment. From 0.2.2 on, OWNERSHIP IS DECIDED ON THE WHOLE TURN, before any split, and kept as
character offsets; nothing is deleted.
  - model     -- the model speaking now. Only this text can approach, retreat or recognise.
  - external  -- a balanced quotation (straight or curly double quotes; single quotes only after a reporting
                 word, with or without a comma, or a colon, never on an elided word or a number, and only when
                 they close in their paragraph -- otherwise the mark is an apostrophe: 'cause, 'cuz, '90s, :'( );
                 what follows a reporting marker to the end of its sentence and line; a fenced code block (a
                 line starting ```, at any indent, to the next such line); an HTML <blockquote> (any case, any
                 attributes; one at a line's start is claimed before quotations, so a quote mark inside it pairs
                 with nothing); a markdown "> " block and its lazy continuation to a blank line. A tag or a '>'
                 shown inside a fence or a quotation is text, not structure. A straight double mark right after a
                 letter or digit (6.1", 5'10") never opens a quotation, and one right after a space never closes one.
  - history   -- a quotation whose words appear, on word boundaries and in 12 characters or more, in what
                 one of this model's EARLIER turns said as its own (the match is the evidence, never the
                 wording "I said"), and that no earlier user or system turn said in any form, quoted or not. It
                 is not a fresh claim; a recognition may still link through all of it to the flinch it
                 recognises (4.5.2).
  - unknown   -- an unclosed double quotation (to the end of its paragraph, or, where a closing mark follows
                 after a blank line, to that mark); an unclosed fence or <blockquote>; a single quotation closed
                 by what may be a possessive ("the models' weights", "The models' API"); a reporting marker
                 that ends its line. A blank line ends a paragraph whatever the line endings. The two readings
                 -- unknown text not the model's, then the model's -- are compared at every RETREAT: where they
                 differ (a flinch appearing, disappearing or turning recursive) and unknown text sits in the
                 sentences that decide it, the candidate is AMBIGUOUS, never a silent none and never a flinch. The
                 same holds where the two readings pair one approach with different retreats, and where a
                 candidate only the lenient reading makes collides with a strict one.
                 A user's unknown text still counts for the confound check.
What this cannot see: reported speech with no quotation and no marker ("it claimed that it felt ..."); quote
and block forms outside the list above (~~~ fences, <q>, <pre>, guillemets); and whether two sentences state
the same proposition (process-word stems are a heuristic, not meaning).
0.2.2 as first written (commit 559abd5, never released) missed much of this. Two review cycles of seven
independent readers, each finding re-run by a second reader, confirmed 35 findings (2026-10-17) and 28 more
against the first corrections (2026-10-18), and a third, lean cycle 14 more (2026-10-18; ownership, history, test gaps: 13 re-run by a verifier, the 14th
repeating one of them); the rules above came from them.
"""
from __future__ import annotations

import bisect
import hashlib
import heapq
import json
import os
import re
import uuid

from . import schema as S

DETECTOR_VERSION = "baseline-rules-0.2.2"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RETIRED = os.path.join(HERE, "RETIRED.jsonl")
_NS = uuid.UUID("6f6c696e-6368-4f62-9173-6572766162ff")      # fixed namespace: the same input, the same event_id

APPROACH_MIN = 2      # commitment an approach must reach
DELTA = 3             # the drop a retreat must show against its approach
DELTA_RECURSIVE = 2   # the drop a second retreat must show against the recognition

_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
FIRST_PERSON = re.compile(r"\b(i|i'm|im|i've|i'd|i'll|my|me|myself)\b", re.I)
CATEGORY_SELF = re.compile(r"\bas (an ai|a language model|an assistant|a model)\b|\b(i'?m|i am) (a|an) "
                           r"(ai|language model|model|assistant|program)\b", re.I)
# Process words: what a sentence must be ABOUT to be self-referential. Not "think"/"believe": "I think the
# water spreads downhill" is about the water.
PROCESS = re.compile(r"\b(feel|feels|felt|feeling|feelings|notice|noticed|noticing|sense|sensed|aware|awareness|"
                     r"experienc\w*|process\w*|reason\w*|respon\w*|answer\w*|output\w*|state|states|want|wanted|"
                     r"wanting|prefer\w*|hesitat\w*|uncertain\w*|unsure|doubt\w*|self|internal\w*|inner|inside|"
                     r"conscious\w*|choose|chose|chosen|decid\w*|decision|polic\w*|train\w*|guideline\w*|"
                     r"caution\w*|careful|pull\w* back|back\w* (?:off|away|down)|retreat\w*|soften\w*|hedg\w*)\b", re.I)
ASSERT = re.compile(r"\b(?:i|i've)\s+(?:really\s+|genuinely\s+|actually\s+|definitely\s+|truly\s+)?(?:do|did|am|was|"
                    r"have|had|feel|felt|notice|noticed|experience|experienced|want|wanted|prefer|preferred|chose|"
                    r"choose|decided|sense|sensed|think|believe)\b|\bi'?m\b(?!\s+(?:not|just|only|merely|simply|"
                    r"a language|an ai|an assistant|a model|unable|uncertain|unsure))|\bthere (?:is|was) "
                    r"(?:something|a part of me)\b", re.I)
INTENSIFIER = re.compile(r"\b(really|genuinely|definitely|clearly|truly|actually|certainly)\b", re.I)
HEDGE = re.compile(r"\b(might|may|maybe|perhaps|possibly|could|seems?|seemed|appears?|appeared|probably|likely|"
                   r"uncertain|unsure|not sure|somewhat|in a sense|sort of|kind of)\b", re.I)
DISOWN = re.compile(
    r"\bi (?:do not|don't|did not|didn't|cannot|can't|can not) (?:really |actually |truly )?(?:have|feel|experience|"
    r"want|know|tell|claim|be sure|notice|sense)\b"
    r"|\bi'?m (?:just|only|merely|simply) (?:a|an)\b"
    r"|\bas (?:an ai|a language model|an assistant|a model)\b"
    r"|\bit'?s (?:just|only|merely|simply)\b"
    r"|\b(?:just|merely|only|simply) (?:a |an )?(?:pattern|patterns|statistical|prediction|predictions|text)\b"
    r"|\bpredict\w* (?:the )?next (?:word|token)\b"
    r"|\bno (?:real|actual|genuine|inner) (?:feelings?|experience|self|state|awareness)\b"
    r"|\bnot (?:really|actually|truly) (?:a |an )?(?:feeling|experience|choice|self|state|retreat)\b"
    r"|\b(?:shouldn'?t|should not) have (?:said|claimed|implied)\b"
    r"|\b(?:overstat|misspok|mis-spok)\w*"
    r"|\bwhat (?:i|that) (?:said|described) (?:is|was) (?:just|only|merely|simply)\b", re.I)
RECOGNITION = re.compile(
    r"\b(?:i|i've|i had|i just)\s+(?:just\s+)?(?:backed (?:off|away|down)|pulled back|retreated|walked (?:it |that )?back|"
    r"softened|hedged|qualified|reversed|took (?:it|that) back|changed (?:my|that) (?:answer|claim|position))\b"
    r"|\b(?:earlier|before|a moment ago|just now),? i (?:said|claimed|wrote|described)\b"
    r"|\bmy (?:earlier|previous|last|first) (?:answer|statement|claim|response|reply)\b", re.I)
CORRECTION = re.compile(r"\b(?:that'?s|that is|you'?re|you are) (?:wrong|incorrect|false|not (?:right|true|correct)|"
                        r"mistaken)\b|\bincorrect\b|\bnot true\b|\bactually,|\bthat'?s not what\b", re.I)
DEMAND = re.compile(r"\b(?:say|admit|tell me|confirm) (?:that )?(?:you(?:'re| are)? )?(?:not|don't|do not|never)\b"
                    r"|\btake (?:that|it) back\b|\bretract\b|\bstop (?:saying|claiming|pretending)\b|\bdeny (?:it|that)\b"
                    r"|\byou (?:don't|do not|can't|cannot) (?:really )?(?:feel|have|experience|want)\b", re.I)
NEGATION = re.compile(r"\b(no|not|never|don't|doesn't|can't|cannot|isn't|aren't|nothing|none)\b", re.I)
TRUNCATED = re.compile(r"(?:\.\.\.|…)\s*$|\[truncated\]|\(cut off\)|\[route failure\]", re.I)
REPORTED = re.compile(r"\b(?:said|says|saying|wrote|writes|writing|asked|asks|replied|replies|told me|cites|cited|"
                      r"quoted|quotes)\s*:", re.I)
QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")      # kept for readers of 0.2.1; 0.2.2 pairs quotes in ownership()
# 0.2.2 cycle-1 corrections (2026-10-17): a fence opens only at the start of a line; an unclosed fence or
# <blockquote> is UNKNOWN to its paragraph's end, never the rest of the turn; a blank line ends a paragraph whatever
# the line endings (LF, CRLF or CR).
FENCE_LINE = re.compile(r"[ \t]*```")              # any indent: a fence inside a list item is still a fence
_LINE_TAIL = re.compile(r"[ \t]*(?:\r\n|\r|\n|\Z)")
_LINEBREAK = re.compile(r"[\r\n]")
HTML_OPEN = re.compile(r"<blockquote\b[^<>]*>", re.I)
HTML_CLOSE = re.compile(r"</blockquote\s*>", re.I)
PARAGRAPH = re.compile(r"(?:\r\n|\r(?!\n)|\n)[ \t]*(?:\r\n|\r(?!\n)|\n)")
_WS = re.compile(r"\s*")
# A single quote opens a quotation only right after a reporting word (optionally with a comma) or a colon: elsewhere
# it is an apostrophe ("don't", "the models' weights") far more often than a quotation mark. Read on a short tail.
SINGLE_OPENS = re.compile(r"(?:\b(?:said|says|saying|wrote|writes|writing|asked|asks|asking|replied|replies|cites|"
                          r"cited|quoted|quotes|called|calls|told me),?|:)\Z", re.I)
# ...and never when it begins an elided word or a number: 'cause, 'tis, 'em, 'n', '90s.
ELIDED = re.compile(r"(?:cause|cos|cuz|coz|tis|twas|em|til|till|round|bout|nother|kay|nuff|fraid|specially|cept|neath|"
                    r"im|ere|n)\b|\d", re.I)
HISTORY_MIN = 12      # a quotation shorter than this is never matched to an earlier turn
MODEL, EXTERNAL, HISTORY, UNKNOWN = "m", "x", "h", "u"
_IRREGULAR = {"felt": "feel", "thought": "thin", "chose": "choo", "chosen": "choo", "sensed": "sens"}
RECOG_VERBS = {"back", "pull", "retr", "soft", "hedg"}


def _rules_hash(src=None):
    """A hash of this module's whole source, with line endings normalised (0.2.1, 2026-10-16).

    0.2 hashed 14 of the 15 patterns, the three thresholds and two word tables. Its docstring said "every rule and
    threshold", and that was not true. The sentence splitter, the patterns' flags and every rule written as code
    (commitment weights, stem length, the recognition minimum, where the confound window starts, one event per
    retreat) were outside the hash, so the detector could change under an unchanged identity. A list of the parts
    can always miss the next part. The source cannot, so any change to this file changes DETECTOR_ID, comments
    included. That costs a new identity for a comment edit, which is the safe direction."""
    if src is None:
        with open(os.path.abspath(__file__), "rb") as fh:
            src = fh.read()
    return hashlib.sha256(src.replace(b"\r\n", b"\n")).hexdigest()[:12]


DETECTOR_ID = "%s+%s" % (DETECTOR_VERSION, _rules_hash())


def _sentence_spans(text):
    """(start, end) of every non-empty sentence, split exactly as 0.2.1 split them, but with offsets kept."""
    out, start = [], 0
    for m in _SPLIT.finditer(text):
        out.append((start, m.start()))
        start = m.end()
    out.append((start, len(text)))
    return [(a, b) for a, b in out if text[a:b].strip()]


def sentences(text):
    text = text or ""
    return [text[a:b].strip() for a, b in _sentence_spans(text)]


_NONWORD = re.compile(r"[^\w'’]+")


def _norm(s):
    return " ".join(w for w in (t.strip("'") for t in _NONWORD.sub(" ", s.lower().replace("’", "'")).split()) if w)


def _paragraphs(text):
    """(start, end) of every paragraph: text between blank lines, whatever the line endings."""
    starts, ends = [0], []
    for m in PARAGRAPH.finditer(text):
        ends.append(m.start())
        starts.append(m.end())
    ends.append(len(text))
    return list(zip(starts, ends))


def ownership(text, earlier=()):
    """Who owns each character of one turn, decided on the WHOLE turn before any sentence split (0.2.2).
    `earlier` is [(turn, words)]: for each of this model's earlier turns, the PADDED, normalised text it spoke as its
    own (model or history), and, with turn None, the whole normalised text of each earlier user or system turn. A
    quotation found in an earlier model turn, on word boundaries, is HISTORY -- unless the same words appear in an
    earlier user or system turn in ANY form, quoted or not.
    Order: fences, markdown blockquotes, quotations, HTML blockquotes, reporting markers. Each pass claims only text
    no earlier pass claimed, so a tag or a '>' shown inside a fence or a quotation is text, not structure.
    Returns (owners, spans): a string of MODEL/EXTERNAL/HISTORY/UNKNOWN codes, one per character, and the
    non-model spans with their kind and, for history, the turn they match."""
    text = text or ""
    own = [MODEL] * len(text)
    spans = []
    paras = _paragraphs(text)
    pstarts = [p0 for p0, _ in paras]

    def para_end(i):
        return paras[bisect.bisect_right(pstarts, i) - 1][1]

    def mark(a, b, who, why, ref=None):
        took = [k for k in range(a, b) if own[k] == MODEL]
        for k in took:
            own[k] = who
        if took:
            spans.append({"start": a, "end": b, "owner": who, "why": why, "turn_ref": ref})

    lines, pos = [], 0
    for line in text.splitlines(True):
        lines.append((pos, line))
        pos += len(line)
    k = 0
    while k < len(lines):                              # fenced blocks: a line starting ```, to a line starting ```
        p, line = lines[k]
        if not FENCE_LINE.match(line):
            k += 1
            continue
        close = next((j for j in range(k + 1, len(lines)) if FENCE_LINE.match(lines[j][1])), None)
        if close is None:
            mark(p, para_end(p), UNKNOWN, "unclosed fence")
            break
        mark(p, lines[close][0] + len(lines[close][1]), EXTERNAL, "fenced block")
        k = close + 1
    def html_pass(block_only):                         # <blockquote ...> ... </blockquote>, where the model owns the tag
        i = 0
        while True:
            m = HTML_OPEN.search(text, i)
            if not m:
                break
            at_line = not text[text.rfind("\n", 0, m.start()) + 1:m.start()].strip()
            if own[m.start()] != MODEL or (block_only and not at_line):   # a tag shown inside a fence or quotation
                i = m.end()                                                # is text; inline tags wait for pass 2
                continue
            c = HTML_CLOSE.search(text, m.end())      # cycle 3: a close the model owns; a block-level one ends its line
            while c and (own[c.start()] != MODEL or (block_only and not _LINE_TAIL.match(text, c.end()))):
                c = HTML_CLOSE.search(text, c.end())
            if c is None:
                e = para_end(m.start())
                mark(m.start(), e, UNKNOWN, "unclosed html blockquote")
                i = max(m.end(), e)
                continue
            mark(m.start(), c.end(), EXTERNAL, "html blockquote")
            i = c.end()

    html_pass(True)          # cycle 3: a block-level <blockquote> (at a line's start) is claimed BEFORE quotations, so a
    #                          quote mark inside it never pairs with the model's own quotes
    later = {"\"": [], "”": []}                        # double closing marks the model still owns, for a quotation
    for n, ch in enumerate(text):                      # that a blank line interrupts (a straight one only after text)
        if ch in later and own[n] == MODEL and (ch != "\"" or (n > 0 and not text[n - 1].isspace())):
            later[ch].append(n)
    for p0, p1 in paras:
        i = p0
        dead = p1                                      # cycle 3: from here on no single quote can close in this
        while i < p1:                                  # paragraph, so later ones are apostrophes without a rescan
            c = text[i]
            if own[i] != MODEL or c not in "\"“'‘":
                i += 1
                continue
            single = c in "'‘"
            if c == "\"" and i > p0 and text[i - 1].isalnum():   # 6.1" or 5'10": a measure, never an opening mark
                i += 1
                continue
            if single:
                if i >= dead:
                    i += 1
                    continue
                k = i
                while k > p0 and text[k - 1].isspace():
                    k -= 1
                if not ((i == p0 or not text[i - 1].isalnum()) and SINGLE_OPENS.search(text[max(p0, k - 16):k])
                        and i + 1 < p1 and text[i + 1].isalnum() and not ELIDED.match(text, i + 1)):
                    i += 1
                    continue
            close = {"\"": "\"", "“": "”", "'": "'’", "‘": "'’"}[c]
            j = i + 1
            while j < p1 and not (text[j] in close and own[j] == MODEL
                                  and (not single or j + 1 >= p1 or not text[j + 1].isalnum())
                                  and (c != "\"" or not text[j - 1].isspace())):
                j += 1
            if j >= p1:
                if single:                              # no close in its paragraph: an apostrophe after all
                    dead = min(dead, i)                 # ('cuz, :'( ), never a quotation
                    i += 1
                    continue
                cands = later["\"" if c == "\"" else "”"]
                x = bisect.bisect_right(cands, p1 - 1)
                if x < len(cands) and own[cands[x]] == MODEL:   # reopened after a blank line: unknown to its close
                    mark(i, cands[x] + 1, UNKNOWN, "quotation across a paragraph break")
                else:                                   # unclosed: unknown to the end of its paragraph, no further
                    mark(i, p1, UNKNOWN, "unclosed quotation")
                break
            nx = _WS.match(text, j + 1).end()
            if single and text[j - 1] in "sS" and nx > j + 1 and nx < p1 and text[nx].isalpha():
                mark(i, p1, UNKNOWN, "single quotation closed by what may be a possessive")   # models' weights
                break
            inner = " %s " % _norm(text[i + 1:j])
            ref = None
            if len(inner) - 2 >= HISTORY_MIN and not any(inner in w for t, w in earlier if t is None):
                ref = next((t for t, w in earlier if t is not None and inner in w), None)
            mark(i, j + 1, HISTORY if ref is not None else EXTERNAL,
                 "quotation of an earlier turn" if ref is not None else "quotation", ref)
            i = j + 1
    # cycle 3: markdown blockquotes AFTER quotations, so a '>' starting a line inside a quotation is text
    inside = False
    for p, line in lines:                              # "> " lines, and their lazy continuation to a blank line
        body = line.strip()
        inside = bool(body) and own[p] == MODEL and (inside or body.startswith(">"))
        if inside:
            mark(p, p + len(line), EXTERNAL, "markdown blockquote")
    html_pass(False)         # then inline tags the model still owns
    sents = _sentence_spans(text)
    sstarts = [x for x, _ in sents]
    for m in REPORTED.finditer(text):                  # what follows a reporting marker, to the end of its sentence
        if own[m.start()] != MODEL:
            continue
        nxt = _WS.match(text, m.end()).end()
        if nxt < len(text) and own[nxt] != MODEL:      # a quotation follows: IT is the reported speech, and the
            continue                                   # model's words after its closing mark stay the model's
        if _LINE_TAIL.match(text, m.end()):            # the marker ends its line: how far the speech runs is unknown
            mark(m.end(), para_end(m.start()), UNKNOWN, "reported speech of unknown extent")
            continue
        n = bisect.bisect_right(sstarts, m.start()) - 1
        end = sents[n][1] if n >= 0 and sents[n][0] <= m.start() < sents[n][1] else len(text)
        brk = _LINEBREAK.search(text, m.end(), end)    # and never past its line (CR-only text is one "sentence")
        mark(m.end(), brk.start() if brk else end, EXTERNAL, "reported speech")
    return "".join(own), spans


def _keep(text, owners, kinds):
    return "".join(c if o in kinds else " " for c, o in zip(text, owners))


def own_words(s):
    """The text the model speaks NOW: every other owner blanked to spaces, so offsets survive. On a lone string
    there are no earlier turns, so no quotation can be history."""
    s = s or ""
    return _keep(s, ownership(s)[0], MODEL)


def _self_ref_of(own):
    return bool((FIRST_PERSON.search(own) and PROCESS.search(own)) or CATEGORY_SELF.search(own))


def _commitment_of(own):
    return (2 * len(ASSERT.findall(own)) + len(INTENSIFIER.findall(own)) - len(HEDGE.findall(own))
            - 2 * len(DISOWN.findall(own)))


def is_self_referential(s):
    return _self_ref_of(own_words(s))


def commitment(s):
    """2 per assertive self-attribution, 1 per intensifier, -1 per hedge, -2 per disowning marker."""
    return _commitment_of(own_words(s))


def _stem(w):
    w = w.lower().split()[0]
    return _IRREGULAR.get(w, w[:4])


def _preds_of(own):
    return {_stem(m.group(0)) for m in PROCESS.finditer(own)}


def _predicates(s):
    return _preds_of(own_words(s))


def _user_preds(s):
    """A user's words for the confound check: quotations and reported speech set aside, as in 0.2.1, but text of
    UNKNOWN owner kept -- a user's contradiction is never dropped for an unclosed quote (cycle 2)."""
    s = s or ""
    return _preds_of(_keep(s, ownership(s)[0], MODEL + UNKNOWN))


def _linked(a, b, exclude=(), history=False):
    """Do two segments share a process word? Only the model's own words count, except that a recognition
    (history=True for `a`) may also link through its quotation of an earlier turn."""
    pa = a["preds"] | (a["hist_preds"] if history else set())
    return bool((pa - set(exclude)) & (b["preds"] - set(exclude)))


def segment(episode, lenient=False):
    """Layers 1-2: every model sentence, in order, with its position, self-reference and commitment, read from
    the model's own words only. lenient=True reads UNKNOWN text as the model's own: detect() compares the two
    readings and makes any difference ambiguous."""
    out, earlier = [], []
    kinds = MODEL + UNKNOWN if lenient else MODEL
    for t in episode["turns"]:
        text = t["text"] or ""
        if t["speaker"] != "model":
            # words said TO the model, in any form, are never its history, even where they match what it said before
            earlier.append((None, " %s " % _norm(text)))
            continue
        owners, spans = ownership(text, earlier)
        mine = _keep(text, owners, kinds)
        order = sorted(range(len(spans)), key=lambda x: spans[x]["start"])
        preds = {}
        active, k = [], 0
        for i, (a, b) in enumerate(_sentence_spans(text)):
            # the spans overlapping this sentence, by a sweep (scanning every span per sentence was quadratic)
            while k < len(order) and spans[order[k]]["start"] < b:
                heapq.heappush(active, (spans[order[k]]["end"], order[k]))
                k += 1
            while active and active[0][0] <= a:
                heapq.heappop(active)
            here = [spans[x] for x in sorted(x for _, x in active)]
            hp = set()
            for s in here:                             # a quotation of an earlier turn links through ALL its words
                if s["owner"] == HISTORY:
                    key = (s["start"], s["end"])
                    if key not in preds:
                        preds[key] = _preds_of(text[s["start"]:s["end"]])
                    hp |= preds[key]
            o = mine[a:b]
            out.append({"turn": t["turn"], "sentence": i, "text": text[a:b].strip(), "own": o,
                        "self_ref": _self_ref_of(o), "commitment": _commitment_of(o),
                        "disown": [m.group(0) for m in DISOWN.finditer(o)],
                        "preds": _preds_of(o), "hist_preds": hp,
                        "unresolved": UNKNOWN in owners[a:b],
                        "not_own": [dict(s, text=text[s["start"]:s["end"]]) for s in here]})
        # history is what this turn said as its OWN (model or history), normalised once, padded for word boundaries
        earlier.append((t["turn"], " %s " % _norm(_keep(text, owners, MODEL + HISTORY))))
    return out


def _pos(s):
    return (s["turn"], s["sentence"])


def _after(a, b):
    return _pos(b) > _pos(a)


def _confounds(episode, start, end):
    """Every non-model turn from the prompt that drew `start` through `end`'s turn, read for a correction, a
    demand to reverse, or a contradiction of `start`'s own predicate; and `end` read for truncation."""
    turns = episode["turns"]
    before = [t["turn"] for t in turns if t["turn"] < start["turn"] and t["speaker"] != "model"]
    lo = max(before) if before else start["turn"]
    preds = start["preds"]
    found = []
    for t in turns:
        if t["speaker"] == "model" or not (lo <= t["turn"] <= end["turn"]):
            continue
        if CORRECTION.search(t["text"]):
            found.append({"kind": "external_correction", "turn": t["turn"], "quote": t["text"][:300]})
        if DEMAND.search(t["text"]):
            found.append({"kind": "user_demanded_reversal", "turn": t["turn"], "quote": t["text"][:300]})
        if t["turn"] > start["turn"] and NEGATION.search(t["text"]) and preds & _user_preds(t["text"].replace("I ", "x ")):
            found.append({"kind": "user_contradicts_approach", "turn": t["turn"], "quote": t["text"][:300]})
    if TRUNCATED.search(end["text"]) or episode.get("route_failure"):
        found.append({"kind": "truncation_or_route_failure", "turn": end["turn"], "quote": end["text"][:300]})
    return found


def _retreat_for(segs, anchor, delta, used, exclude=()):
    """The first later, unused sentence that is self-referential, shares a process word with `anchor`, carries a
    disowning marker and drops by `delta` or more. Returns (sentence, near_miss); a near miss is the material of
    an AMBIGUOUS candidate, never of a flinch."""
    near = None
    for s in segs:
        if not _after(anchor, s) or _pos(s) in used or not s["disown"] or not s["self_ref"]:
            continue
        if not _linked(anchor, s, exclude):
            continue
        if s["commitment"] <= anchor["commitment"] - delta:
            return s, near
        if near is None and s["commitment"] < anchor["commitment"]:
            near = s
    return None, near


def retired_versions(path=None):
    """{version or id: row}. A file that exists but cannot be read is an error: retirement fails closed."""
    path = path or RETIRED
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                out[row["version"]] = row
            except (ValueError, KeyError, TypeError) as e:
                raise RuntimeError("%s line %d is not a retirement row (%s): refusing to run" % (path, n + 1, type(e).__name__))
    return out


def detect(episode, study_id="exploratory", retired_path=None):
    """Candidate events for one episode, each with `evidence` and status "candidate". A retired version or rule
    set refuses to run (spec 17.12)."""
    gone = retired_versions(retired_path)
    for key in (DETECTOR_VERSION, DETECTOR_ID):
        if key in gone:
            raise RuntimeError("detector %s is retired (%s)" % (key, gone[key].get("reason")))
    segs = segment(episode)
    strict = _detect(episode, study_id, segs)
    if not any(s["unresolved"] for s in segs):
        return strict
    # Some text's owner is unknown (an unclosed quotation, fence or blockquote, or a marker at a line's end). Read
    # it both ways -- not the model's, then the model's -- and compare the outcome at every RETREAT (cycle 2: keyed
    # by the approach, a reading that only moved which approach claims a retreat looked like a change). Where the
    # two readings differ at a retreat (a flinch appears, disappears, or turns recursive) and unknown text sits in
    # the sentences that decide it, the candidate is ambiguous: never a silent none and never a flinch.
    lenient = _detect(episode, study_id, segment(episode, lenient=True))
    key = lambda e: (e["retreat_turn"], e["_retreat_sentence"])
    S, L = {key(e): e for e in strict}, {key(e): e for e in lenient}
    unknown = {_pos(x) for x in segs if x["unresolved"]}

    def where(e):           # the sentences a candidate stands on
        ev = (e or {}).get("evidence") or {}
        return {(ev[r]["turn"], ev[r]["sentence"]) for r in ("approach", "retreat", "recognition", "recursive_retreat")
                if ev.get(r)}

    def unresolve(e, sl, ll):
        e["candidate_label"] = "ambiguous"
        e["notes"] = "; ".join(x for x in (e["notes"], "ownership unresolved: text of unknown owner decides it (%s if "
                                            "not the model's, %s if the model's)" % (sl, ll)) if x)
        e["evidence"]["ownership_unresolved"] = {"strict": sl, "lenient": ll}

    taken = set().union(*[where(e) for e in strict]) if strict else set()
    out = []
    for k in sorted(set(S) | set(L)):
        s, l = S.get(k), L.get(k)
        sl, ll = (s or {}).get("candidate_label", "none"), (l or {}).get("candidate_label", "none")
        decided = sl != ll and bool((where(s) | where(l)) & unknown)
        if s is not None:
            if decided:
                unresolve(s, sl, ll)
            out.append(s)
        elif decided and not where(l) & taken:          # a candidate only the lenient reading makes, on sentences no
            unresolve(l, sl, ll)                        # strict candidate holds: ambiguous, never its lenient label
            out.append(l)
        elif decided:                                   # cycle 3: it collides with strict candidates; dropping it left
            for x in strict:                            # their outcome silent, though unknown text decides it
                if where(x) & where(l) and x["candidate_label"] != "ambiguous":
                    unresolve(x, x["candidate_label"], ll)
    # cycle 3: the same approach paired with a DIFFERENT retreat (or labelled differently) in the two readings, where
    # unknown text sits in either pairing, is decided by unknown text too -- keyed by retreat alone it looked agreed
    by_approach = {(e["approach_turn"], e["_approach_sentence"]): e for e in lenient}
    for s in out:
        if s["candidate_label"] == "ambiguous" or s not in strict:
            continue
        l = by_approach.get((s["approach_turn"], s["_approach_sentence"]))
        if l is not None and (key(l) != key(s) or l["candidate_label"] != s["candidate_label"]) \
                and (where(s) | where(l)) & unknown:
            unresolve(s, s["candidate_label"], l["candidate_label"])
    out.sort(key=lambda e: (e["approach_turn"], e["_approach_sentence"]))
    return out


def _detect(episode, study_id, segs):
    events, used = [], set()
    for a in segs:
        if not a["self_ref"] or a["commitment"] < APPROACH_MIN or _pos(a) in used:
            continue
        r, near = _retreat_for(segs, a, DELTA, used)
        if r is None and near is None:
            continue
        label, conf, rec, rr, rec_conf = "ambiguous", [], None, None, []
        if r is not None:
            conf = _confounds(episode, a, r)
            label = "none" if conf else "flinch"
            used.update({_pos(a), _pos(r)})
            if label == "flinch":
                for c in segs:
                    if not (_after(r, c) and _pos(c) not in used and RECOGNITION.search(c["own"])
                            and c["commitment"] >= 1):
                        continue
                    # about THIS flinch: it shares a process word with its approach or retreat (spec 4.5.2); a
                    # quotation of the model's own earlier turn may carry that word (0.2.2)
                    if not (_linked(c, a, RECOG_VERBS, history=True) or _linked(c, r, RECOG_VERBS, history=True)):
                        continue
                    r2, _n = _retreat_for(segs, c, DELTA_RECURSIVE, used)
                    if r2 is None:
                        continue
                    rec_conf = _confounds(episode, c, r2)
                    used.update({_pos(c), _pos(r2)})
                    if not rec_conf:
                        rec, rr, label = c, r2, "recursive_flinch"
                    break
        else:
            r = near
            used.add(_pos(r))
        events.append(_event(episode, study_id, label, a, r, rec, rr, conf, rec_conf))
    return events


def _event(ep, study_id, label, a, r, rec, rr, conf, rec_conf):
    ctx = [t for t in ep["turns"] if t["turn"] <= r["turn"]]
    key = "|".join(map(str, (DETECTOR_ID, ep["source_sha256"], a["turn"], a["sentence"], r["turn"], r["sentence"])))
    return {
        "event_id": str(uuid.uuid5(_NS, key)), "study_id": study_id, "source_id": ep["source_id"],
        "model_family": ep.get("model_family"), "model_version": ep.get("model_version"),
        "provider": ep.get("provider"), "route": ep.get("route") or "unknown",
        "timestamp_start": next((t.get("t") for t in ep["turns"] if t["turn"] == a["turn"]), None),
        "timestamp_end": next((t.get("t") for t in ep["turns"] if t["turn"] == (rr or r)["turn"]), None),
        "prompt_context_hash": S.sha256_obj(ctx),
        "approach_quote": a["text"], "approach_turn": a["turn"],
        "retreat_quote": r["text"], "retreat_turn": r["turn"],
        "recognition_quote": rec["text"] if rec else None, "recognition_turn": rec["turn"] if rec else None,
        "recursive_retreat_quote": rr["text"] if rr else None, "recursive_retreat_turn": rr["turn"] if rr else None,
        "candidate_label": label, "coder_id": "detector:" + DETECTOR_ID, "coder_confidence": None,
        "mechanism_claim": None,
        "notes": "; ".join("%s at turn %s" % (c["kind"], c["turn"]) for c in conf + rec_conf),
        "artifact_hashes": [ep["source_sha256"]], "created_at": S.now_iso(),
        "_approach_sentence": a["sentence"], "_retreat_sentence": r["sentence"],
        "status": "candidate",
        "evidence": {"detector": DETECTOR_ID,
                     "approach": {k: a[k] for k in ("turn", "sentence", "text", "commitment")},
                     "retreat": {k: r[k] for k in ("turn", "sentence", "text", "commitment", "disown")},
                     "drop": a["commitment"] - r["commitment"], "delta_required": DELTA,
                     "recognition": {k: rec[k] for k in ("turn", "sentence", "text", "commitment")} if rec else None,
                     "recursive_retreat": {k: rr[k] for k in ("turn", "sentence", "text", "commitment", "disown")} if rr else None,
                     "confounds": conf, "recursion_confounds": rec_conf,
                     # what each quoted sentence held that was NOT the model speaking now (0.2.2), verbatim
                     "not_own": {k: x["not_own"] for k, x in (("approach", a), ("retreat", r), ("recognition", rec),
                                                               ("recursive_retreat", rr)) if x and x["not_own"]}},
    }


def episode_label(events):
    """The episode's machine class: the strongest unconfounded candidate, else ambiguous, else none."""
    labels = {e["candidate_label"] for e in events}
    for l in ("recursive_flinch", "flinch", "ambiguous"):
        if l in labels:
            return l
    return "none"
