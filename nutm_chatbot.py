"""
NUTM Chatbot - a very simple question-answering bot for the
Nigerian University of Technology and Management.

* No API key, no internet, no pip install, no virtual environment.
* Uses only Python's standard library (Python 3.8 or newer).
* How it works (retrieval): the knowledge base is split into entries, every
  entry and your question are turned into TF-IDF word vectors, and the entry
  with the highest cosine similarity is returned as the answer.

Run it:   python nutm_chatbot.py
Keep nutm_knowledge_base.txt in the same folder as this file.
"""

import math
import re
import sys
from collections import Counter
from pathlib import Path

KB_FILE = Path(__file__).with_name("nutm_knowledge_base.txt")
MIN_SCORE = 0.12          # below this the bot says it does not know
SECOND_ANSWER_RATIO = 0.92  # show a second entry if it is almost as good

FALLBACK = (
    "Sorry, I could not find that in my NUTM knowledge base.\n"
    "Please contact NUTM directly:\n"
    "  General: info@nutm.edu.ng | Admissions: admissions@nutm.edu.ng\n"
    "  Postgraduate: pg.admissions@nutm.edu.ng | Phone: +234 906 249 1012"
)

STOPWORDS = set("""
a an the is are was were be been am do does did can could will would should may might
i me my we our you your it its of to in on at for from by with about as and or but if
what which who whom whose why how this that these those there here
nutm please tell give know want need like get have has had also any some
""".split())

# Short forms people type -> words used in the knowledge base
ABBREVIATIONS = {
    "ds": "data science", "se": "software engineering", "ug": "undergraduate",
    "pg": "postgraduate", "msc": "msc postgraduate", "masters": "postgraduate",
    "master": "postgraduate", "bsc": "undergraduate", "cs": "computer science",
    "ft": "full-time", "pt": "part-time", "fulltime": "full-time",
    "parttime": "part-time",
}

# Different words that mean the same thing
SYNONYMS = {
    "cost": "fee", "much": "fee", "where": "address", "teach": "faculty", "teaches": "faculty", "teaching": "faculty", "lecturer": "faculty", "professor": "faculty", "instructors": "faculty", "when": "date", "deadline": "date", "costs": "fee", "tuition": "fee", "price": "fee", "pay": "fee",
    "payment": "fee", "naira": "fee", "charges": "fee", "expensive": "fee",
    "program": "programme",
    "programs": "programme", "programmes": "programme", "degree": "programme",
    "degrees": "programme", "subjects": "curriculum", "modules": "curriculum",
    "syllabus": "curriculum", "requirement": "eligibility",
    "requirements": "eligibility", "qualify": "eligibility",
    "qualification": "eligibility", "email": "contact", "phone": "contact",
    "call": "contact", "number": "contact", "reach": "contact",
    "begin": "start", "commence": "start", "starts": "start",
    "duration": "length", "long": "length", "applying": "apply",
    "admission": "apply", "admissions": "apply", "application": "apply",
    "join": "apply", "register": "apply", "location": "address",
    "located": "address", "hostel": "accommodation", "lecturers": "faculty",
    "professors": "faculty", "teachers": "faculty", "scholarships": "scholarship",
    "bursary": "scholarship", "financial": "scholarship",
}


def stem(word):
    """Very small stemmer so 'programmes' ~ 'programme', 'applying' ~ 'apply'."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]
    return word


def tokenize(text):
    """Lower-case, expand abbreviations, drop stop words, map synonyms, stem."""
    words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    tokens = []
    for w in words:
        for part in ABBREVIATIONS.get(w, w).split():
            part = SYNONYMS.get(part) or SYNONYMS.get(stem(part)) or part
            if part in STOPWORDS:
                continue
            tokens.append(stem(part))
    return tokens


def load_entries(path):
    """Read the knowledge base into a list of {title, keywords, body}."""
    if not path.exists():
        sys.exit(f"Cannot find {path.name}. Put it in the same folder as this script.")
    text = path.read_text(encoding="utf-8")
    entries = []
    current = None
    for line in text.splitlines():
        if line.startswith("### "):
            current = {"title": line[4:].strip(), "keywords": "", "body": []}
            entries.append(current)
        elif current is None or (line.startswith("#") and not line.startswith("###")):
            continue
        elif line.lower().startswith("keywords:"):
            current["keywords"] = line.split(":", 1)[1]
        else:
            current["body"].append(line)
    for e in entries:
        e["body"] = "\n".join(e["body"]).strip()
    return entries


class Retriever:
    def __init__(self, entries):
        self.entries = entries
        self.programmes = [detect_programme(e["title"]) for e in entries]
        # Title words count 3x, keyword words 2x, body words 1x
        self.vectors = []
        for e in entries:
            tokens = (tokenize(e["title"]) * 3
                      + tokenize(e["keywords"]) * 2
                      + tokenize(e["body"]))
            self.vectors.append(Counter(tokens))
        n = len(entries)
        df = Counter()
        for v in self.vectors:
            df.update(v.keys())
        self.idf = {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df.items()}
        self.norms = [self._norm(v) for v in self.vectors]

    def _norm(self, vec):
        return math.sqrt(sum((c * self.idf.get(t, 1.0)) ** 2 for t, c in vec.items()))

    def search(self, question, top_k=2):
        q = Counter(tokenize(question))
        if not q:
            return []
        q_norm = self._norm(q)
        q_prog = detect_programme(question)
        scored = []
        for i, vec in enumerate(self.vectors):
            dot = sum(c * self.idf[t] * vec[t] * self.idf[t]
                      for t, c in q.items() if t in vec)
            score = dot / (q_norm * self.norms[i]) if dot else 0.0
            # If the question names a programme, favour that programme's entries
            # and demote entries that are clearly about a different programme.
            if "overview" in self.entries[i]["title"].lower():
                score *= 0.85  # overviews match everything; prefer specific entries
            if q_prog and self.programmes[i]:
                score *= 1.3 if q_prog & self.programmes[i] else 0.5
            scored.append((score, i))
        scored.sort(reverse=True)
        return [(s, self.entries[i]) for s, i in scored[:top_k]]


# Which programme is an entry / a question about?  (used to boost the right entry)
PROGRAMME_PATTERNS = {
    "ds": r"data science|\bds\b",
    "se": r"software engineering|\bse\b",
    "mba": r"\bmba\b|business administration",
    "ug": r"undergrad|\bug\b|\bbsc\b|b\.sc|jamb|utme|\bsiwes\b",
}


def detect_programme(text):
    """Return the set of programmes mentioned in a piece of text."""
    text = text.lower()
    return {k for k, pat in PROGRAMME_PATTERNS.items() if re.search(pat, text)}


GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
GOODBYES = {"bye", "goodbye", "exit", "quit", "q", "thanks bye"}
HELP_TEXT = (
    "You can ask me about NUTM, for example:\n"
    "  - What postgraduate programmes does NUTM offer?\n"
    "  - How much is the MSc Data Science tuition?\n"
    "  - What are the entry requirements for undergraduate programmes?\n"
    "  - How do I apply for the MBA?\n"
    "  - Where is the campus? / How do I contact admissions?\n"
    "Type 'quit' to leave."
)


def answer(retriever, question):
    if re.fullmatch(r"(what|who)(\s+is|'s|\s+are)?\s+(nutm|this university|the university)\s*[?.!]*", question.lower().strip()):
        for e in retriever.entries:
            if e["title"] == "About NUTM":
                return e["body"]
    results = retriever.search(question)
    if not results or results[0][0] < MIN_SCORE:
        return FALLBACK
    best_score, best = results[0]
    reply = f"{best['body']}"
    if len(results) > 1:
        second_score, second = results[1]
        if second_score >= best_score * SECOND_ANSWER_RATIO and second_score >= MIN_SCORE:
            reply += f"\n\nRelated: {second['title']}\n{second['body']}"
    return reply


def main():
    try:  # make the Naira sign print correctly on Windows consoles
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    retriever = Retriever(load_entries(KB_FILE))
    print("=" * 60)
    print(" NUTM Assistant - ask me about NUTM programmes, fees, admission")
    print(" Type 'help' for examples or 'quit' to exit.")
    print("=" * 60)
    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Goodbye!")
            break
        if not question:
            continue
        low = question.lower().strip("!.? ")
        if low in GOODBYES:
            print("Bot: Goodbye! Good luck with your NUTM journey.")
            break
        if low in GREETINGS:
            print("Bot: Hello! I can answer questions about NUTM. Type 'help' for examples.")
            continue
        if low == "help":
            print("Bot:", HELP_TEXT)
            continue
        print("\nBot:", answer(retriever, question))


if __name__ == "__main__":
    main()
