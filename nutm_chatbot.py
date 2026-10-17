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

import difflib
import math
import re
import sys
from collections import Counter
from pathlib import Path

KB_FILE = Path(__file__).with_name("nutm_knowledge_base.txt")
MIN_SCORE = 0.25          # below this the bot says it does not know
MAX_TYPO_FIXES = 12       # spelling corrections attempted per question
MAX_QUESTION_CHARS = 300  # longer questions are cut off
MAX_UNKNOWN_SHARE = 0.5   # more unknown words than this and the bot says it does not know
SECOND_ANSWER_RATIO = 0.92  # show a second entry if it is almost as good

FALLBACK = (
    "Sorry, I could not find an answer to that. I am the NUTM Assistant, so I can help with "
    "NUTM programmes, fees, admission, entry requirements and TEDLab. "
    "For example, try: How much is the MBA?\n\n"
    "For anything else, please contact NUTM:\n"
    "Admissions: admissions@nutm.edu.ng\n"
    "Postgraduate: pg.admissions@nutm.edu.ng\n"
    "Phone: +234 906 249 1012"
)

# Short everyday messages the bot answers directly (checked before searching)
R_HELP = (
    "I can answer questions about NUTM, for example:\n"
    "- How much is the MSc Data Science tuition?\n"
    "- How do I apply for the MBA?\n"
    "- What are the entry requirements for B.Sc. Accounting?\n"
    "- What is TEDLab?\n"
    "- Where is the campus and how do I contact admissions?\n"
    "You can also ask follow-up questions such as \"what about the MBA?\" or \"tell me more\"."
)
R_GREET = "Hello! I am the NUTM Assistant. Ask me about NUTM programmes, fees, admission, requirements, TEDLab or how to contact admissions."
R_MORNING = "Good morning! I am the NUTM Assistant. How can I help you with NUTM today?"
R_AFTERNOON = "Good afternoon! I am the NUTM Assistant. How can I help you with NUTM today?"
R_EVENING = "Good evening! I am the NUTM Assistant. How can I help you with NUTM today?"
R_NIGHT = "Good night! Come back any time with your NUTM questions."
R_DAY = "Good day! I am the NUTM Assistant. How can I help you with NUTM today?"
R_WELLDONE = "Thank you, I am glad I could help! Ask me anything else about NUTM."
R_OK = "Great! Ask me anything else about NUTM."
R_YES = "Okay! What would you like to know about NUTM?"
R_NO = "Alright. If you think of anything else about NUTM, just ask!"
R_SORRY = "No problem at all! How can I help you with NUTM?"
R_LAUGH = "Glad you are enjoying this! What else would you like to know about NUTM?"
R_WOW = "I hope that helps! What else would you like to know about NUTM?"
R_THANKS = "You are welcome! Ask me anything else about NUTM."
R_BYE = "Goodbye! Good luck with your NUTM journey."
R_WELCOME = "Thank you! How can I help you with NUTM today?"
R_HOWAREYOU = "I am doing well, thank you! How can I help you with NUTM today?"
R_ABOUT_ME = ("I am the NUTM Assistant, a chatbot that answers questions about the Nigerian University of Technology "
              "and Management (NUTM): programmes, fees, admission, requirements, TEDLab and contacts.")
R_MADE_BY = ("I was built as a student project using Python, from NUTM's public information. I am not an official "
             "NUTM channel, so please confirm important details with NUTM admissions.")
R_BOT = ("I am an automated chatbot, not a person. I answer from NUTM's published information, so please confirm "
         "important details such as fees and deadlines with admissions.")
R_RUDE = ("I am sorry I could not help better. Please try rephrasing your question, or contact NUTM admissions "
          "directly: admissions@nutm.edu.ng")

# (reply, phrases separated by |). Spelling mistakes are tolerated (see small_talk).
SMALL_TALK_PHRASES = [
    (R_GREET, "hy|hii|hiii|heyy|heyyy|hie|hllo|helo|hellow|hallo|hi|hello|hey|hiya|howdy|greetings|yo|sup|hullo|hellooo|hey hey|hello hello|hi hi|hi nutm|hello nutm|hey nutm|"
              "hi assistant|hello assistant|hey assistant|hi bot|hello bot|hey bot|hello friend|hello good people"),
    (R_MORNING, "good morning|morning|goodmorning|gud morning|good morning nutm|morning nutm|top of the morning"),
    (R_AFTERNOON, "good afternoon|afternoon|goodafternoon|gud afternoon"),
    (R_EVENING, "good evening|evening|goodevening|gud evening"),
    (R_NIGHT, "good night|goodnight|night|nite|good nite|night night|sleep well|have a good night|gud night"),
    (R_DAY, "good day|have a nice day|have a good day|nice day|have a great day"),
    (R_WELLDONE, "well done|welldone|good job|great job|nice job|nice work|good work|great work|nice one|bravo|excellent|"
                 "perfect|brilliant|wonderful|awesome|amazing|impressive|fantastic|superb|thats great|that is great|"
                 "you are good|you are great|you are smart|you are amazing|very good|that was helpful|this is helpful|"
                 "helpful|you are helpful|good bot|nice bot|great bot|i like you|i love this|love it|thats good|that is good|"
                 "thats nice|that is nice|good answer|great answer"),
    (R_OK, "ok|okay|okey|k|kk|alright|all right|noted|cool|fine|got it|understood|i see|sure|sure thing|alright then|"
           "okay then|ok then|oh ok|oh okay|i understand|makes sense|i get it|right|good|nice|great|oh i see|ok cool|ok great"),
    (R_YES, "yes|yeah|yep|yup|yes please|of course|definitely|certainly"),
    (R_NO, "no|nope|nah|no thanks|no thank you|not really|nothing|that is all|thats all|that will be all|nothing else|"
           "no more|i am done|am done|that is enough|enough"),
    (R_SORRY, "sorry|my bad|apologies|i am sorry|oops|excuse me|pardon|pardon me|forgive me"),
    (R_LAUGH, "lol|haha|hahaha|hehe|lmao|ha ha|funny|that is funny|thats funny|rofl"),
    (R_WOW, "wow|oh wow|oh|ohh|hmm|hmmm|ah|ahh|aha|interesting|really|is that so|ok wow"),
    (R_THANKS, "thanks|thank you|thank u|thx|thanks a lot|thank you so much|many thanks|much appreciated|thank you very much|"
               "i appreciate|i appreciate it|ok thanks|okay thanks|ok thank you|okay thank you|thanks so much|thanks a million|"
               "thank you sir|thanks alot|tanks|thnx|tnx|thank"),
    (R_BYE, "bye|goodbye|see you|see you later|see ya|cya|take care|bye bye|ok bye|okay bye|thanks bye|talk later|later|"
            "i am leaving|i am going|i have to go|got to go|gotta go|ttyl|until next time"),
    (R_WELCOME, "welcome|you are welcome|no problem|np|no worries|anytime|any time"),
    (R_HOWAREYOU, "how are you|how are you doing|how are you today|how is it going|how do you do|whats up|wassup|wazup|whats good|"
                  "how far|how far na|how you dey|wetin dey|how body|are you ok|are you okay|are you fine|are you well|"
                  "hope you are well|how is your day|how was your day|hows life|how is life|how have you been"),
    (R_ABOUT_ME, "what is your name|whats your name|your name|who are you|what are you|what are you called|tell me about yourself|"
                 "introduce yourself|what should i call you|what do i call you|do you have a name|may i know your name|"
                 "can i know your name|what do they call you|who am i talking to|who am i speaking to"),
    (R_MADE_BY, "who made you|who created you|who built you|who developed you|who designed you|who programmed you|"
                "who is your creator|who owns you|who is your developer|who is your maker|who trained you|who wrote you"),
    (R_BOT, "are you a robot|are you a bot|are you human|are you real|are you a person|are you ai|are you an ai|"
            "is this a bot|is this a robot|is this a real person|am i talking to a human|am i speaking to a person|"
            "are you a real person|are you a chatbot|is this a chatbot|are you alive"),
    (R_HELP, "help|help me|what can you do|what can i ask|what can i ask you|how does this work|how do you work|what do you know|"
             "options|menu|examples|show me examples|i need help|can you help me|can you help|could you help me|"
             "please help|need help|what do you offer|what questions can i ask|how can you help"),
]
_PHRASES = {}
for _reply, _phrases in SMALL_TALK_PHRASES:
    for _p in _phrases.split("|"):
        _PHRASES.setdefault(_p, _reply)
_PHRASE_LIST = list(_PHRASES)
FILLERS = {"nutm", "assistant", "bot", "sir", "ma", "madam", "please", "pls", "plz", "there", "friend", "dear",
           "again", "o", "oh", "na", "abeg", "boss", "chief"}
RUDE_RE = r"\b(stupid|idiot|useless|dumb|rubbish|nonsense|fool|foolish|bad bot|hate you|shut up)\b"


def clean_text(question):
    """Lower-case, drop apostrophes and punctuation, collapse spaces."""
    text = question.lower().replace("'", "").replace("\u2019", "")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())


def small_talk(question):
    """Reply for greetings, thanks, 'okay', 'well done', 'who are you' and so on (spelling mistakes allowed)."""
    text = clean_text(question)
    if not text or len(text) > 60:
        return None
    words = text.split()
    while len(words) > 1 and words[-1] in FILLERS:
        words.pop()
    text = " ".join(words)
    m = re.fullmatch(r"(.+?) (how are you( doing| today)?|how is it going|how far|how you dey|hope you are well)", text)
    if m and m.group(1) in _PHRASES:
        return _PHRASES[m.group(1)] + " I am doing well, thank you."
    if text in _PHRASES:
        return _PHRASES[text]
    if len(words) <= 4 and len(text) >= 4:
        close = difflib.get_close_matches(text, _PHRASE_LIST, n=1, cutoff=0.85)
        if close:
            return _PHRASES[close[0]]
    if len(words) <= 5 and re.search(RUDE_RE, text):
        return R_RUDE
    return None


STOPWORDS = set("""
a an the is are was were be been am do does did can could will would should may might
i me my we our you your it its of to in on at for from by with about as and or but if
what which who whom whose why how this that these those there here
nutm ok okay pls plz sir madam ma dear kindly abeg hello hi hey hiya howdy greetings thanks thank please tell give know involve involves involved mean means explain describe details detail information info want need like get have has had also any some
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
    "cost": "fee", "much": "fee", "bachelor": "undergraduate", "bachelors": "undergraduate", "teach": "faculty", "teaches": "faculty", "teaching": "faculty", "lecturer": "faculty", "professor": "faculty", "instructors": "faculty", "when": "date", "deadline": "date", "costs": "fee", "tuition": "fee", "price": "fee", "pay": "fee",
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
    "bursary": "scholarship", "installment": "instalment", "installments": "instalment", "instalments": "instalment",  "financial": "scholarship",
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


WORD_RE = r"[a-z0-9]+(?:-[a-z0-9]+)*"

# Phrases that mean the same thing are rewritten to one key word before matching
PHRASES = [
    (r"who (can|may|is allowed to) apply|who is eligible|who qualifies|am i eligible", " eligibility "),
    (r"where (is|are)\b", " address "),
    (r"how (many|much) (years|months|semesters|weeks)|how long", " length "),
    (r"what (do|must|should) i need to (study|apply|get in|join|enrol|enroll)", " eligibility "),
]


def tokenize(text, fix=None):
    """Lower-case, (fix typos), expand abbreviations, drop stop words, map synonyms, stem."""
    text = text.lower()
    for pattern, replacement in PHRASES:
        text = re.sub(pattern, replacement, text)
    words = re.findall(WORD_RE, text)
    tokens = []
    for w in words:
        if fix:
            w = fix(w)
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
        self.vocab = set(self.idf)
        self._typo_cache = {}
        # every raw word the bot knows (used to spot and correct spelling mistakes)
        text = " ".join(e["title"] + " " + e["keywords"] + " " + e["body"] for e in entries).lower()
        self.raw_vocab = set(re.findall(WORD_RE, text)) | set(SYNONYMS) | set(ABBREVIATIONS) | STOPWORDS
        self.max_idf = max(self.idf.values())
        self.norms = [self._norm(v) for v in self.vectors]

    def _norm(self, vec):
        # words the knowledge base has never seen count as rare (high weight), so
        # off-topic questions score low instead of matching on one common word
        return math.sqrt(sum((c * self.idf.get(t, getattr(self, 'max_idf', 1.0))) ** 2
                             for t, c in vec.items()))

    def _closest(self, word):
        """Closest known word to a misspelt one (remembered, so repeats are free)."""
        if word not in self._typo_cache:
            close = difflib.get_close_matches(word, self.raw_vocab, n=1, cutoff=0.82)
            if len(self._typo_cache) < 3000:
                self._typo_cache[word] = close[0] if close else word
            else:
                return close[0] if close else word
        return self._typo_cache[word]

    def search_all(self, question):
        budget = [MAX_TYPO_FIXES]  # spell-checking is the slow part: only do a few words

        def fix(word):
            if word in self.raw_vocab or len(word) < 5 or word.isdigit() or budget[0] <= 0:
                return word
            budget[0] -= 1
            return self._closest(word)

        q = Counter(tokenize(question, fix=fix))
        if not q:
            return []
        q_norm = self._norm(q)
        # If most of the question is made of words the bot has never seen, it is
        # probably off-topic: do not guess.
        unknown = sum(c * self.max_idf for t, c in q.items() if t not in self.vocab)
        total = sum(c * self.idf.get(t, self.max_idf) for t, c in q.items())
        if total and unknown / total > MAX_UNKNOWN_SHARE:
            return []
        q_prog = detect_programme(question)
        scored = []
        for i, vec in enumerate(self.vectors):
            dot = sum(c * self.idf[t] * vec[t] * self.idf[t]
                      for t, c in q.items() if t in vec)
            score = dot / (q_norm * self.norms[i]) if dot else 0.0
            # If the question names a programme, favour that programme's entries
            # and demote entries that are clearly about a different programme.
            if "overview" in self.entries[i]["title"].lower():
                score *= 0.7  # overviews match everything; prefer specific entries
            if q_prog and self.programmes[i]:
                score *= 1.3 if q_prog & self.programmes[i] else 0.5
            scored.append((score, i))
        scored.sort(reverse=True)
        return [(sc, self.entries[i]) for sc, i in scored if sc > 0]

    def search(self, question, top_k=2):
        return self.search_all(question)[:top_k]


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


GOODBYES = {"bye", "goodbye", "exit", "quit", "q", "bye bye"}

# ------------------------------------------------------------------------------
# Programme + topic routing, and conversation memory
# ------------------------------------------------------------------------------
PROG_LABEL = {
    "ds": "MSc Data Science", "se": "MSc Software Engineering", "mba": "MBA",
    "ug": "undergraduate programmes",
    "ug:accounting": "B.Sc. Accounting", "ug:economics": "B.Sc. Economics",
    "ug:cs": "B.Sc. Computer Science", "ug:cyber": "B.Sc. Cybersecurity",
    "ug:it": "B.Sc. Information Technology", "ug:business": "B.Sc. Business Administration",
    "ug:entre": "B.Sc. Entrepreneurship",
}
COMPUTING = {"ug:cs", "ug:cyber", "ug:it"}
PROG_PATTERNS = [
    ("mba", r"\bmba\b|master of business administration"),
    ("ds", r"data science|\bds\b"),
    ("se", r"software engineering|\bse\b"),
    ("ug:accounting", r"accounting|accountancy"),
    ("ug:economics", r"economics"),
    ("ug:cyber", r"cyber ?security"),
    ("ug:cs", r"computer science|\bcs\b"),
    ("ug:it", r"information technology|\bit (degree|programme|program|course)|b\.? ?sc\.? (in )?it\b|\bbsc it\b"),
    ("ug:business", r"business administration|business admin"),
    ("ug:entre", r"entrepreneurship (degree|programme|program|course|bsc)|b\.? ?sc\.? (in )?entrepreneurship|bsc entrepreneurship|degree in entrepreneurship"),
    ("ug", r"undergrad|\bug\b|\bbsc\b|b\.? ?sc\b|bachelor|first degree|jamb|utme|siwes"),
]
UG_WORDS = r"undergrad|\bbsc\b|b\.? ?sc\b|jamb|utme|\bug\b"
INTENT_PATTERNS = [
    ("eligibility", r"eligib|requirement|qualif|\bentry\b|prerequisite|criteria|cut ?off|jamb score|utme score|what do i need|need to (study|apply|get in|join)|who can (apply|study|join)|physics|o.?level subjects?"),
    ("fee", r"\bfees?\b|cost|tuition|price|how much|charges|payment|\bpay\b|expensive|afford"),
    ("duration", r"how long|duration|length|\bmonths?\b|\byears?\b|semesters?"),
    ("curriculum", r"course|curriculum|module|subject|syllabus|what (will|do|can) i (learn|study)|taught|credits?|study plan"),
    ("start", r"\bstart|begin|commence|intake|deadline|when (does|do|is|will)|resum"),
    ("admission", r"\bapply|application|admission|admit|enrol|register|\bjoin\b|get in"),
]
INTENT_HINT = {"fee": "tuition fees", "admission": "how to apply admission", "eligibility": "entry requirements eligibility",
               "duration": "how long duration", "curriculum": "courses curriculum", "start": "start date intake"}
PG_PREFIX = {"ds": "MSc Data Science", "se": "MSc Software Engineering", "mba": "MBA"}
PG_KEY = {"fee": "tuition", "admission": "admission", "eligibility": "eligibility",
          "duration": "duration", "curriculum": "curriculum", "start": "start date"}
OTHER_TOPIC = (r"campus|dean|scholarship|partner|alumni|faculty|lecturer|tedlab|contact|email|phone|address|hostel|"
               r"gmat|\bgre\b|siwes|shadow|nsp|vision|mission|accredit|defer|transfer|executive|teach|professor|instructor|tutor")
MODE_RE = r"part[- ]?time|full[- ]?time|online|on[- ]?campus|weekend"
MORE_RE = (r"(tell me )?more( about (it|that|this))?|more details?|more info(rmation)?|elaborate|explain (more|further)|"
           r"go on|continue|what else|anything else|and")
ABOUT_PHRASES = {"nutm", "about nutm", "tell me about nutm", "what is nutm", "who is nutm", "nutm university",
                 "the university", "tell me about the university", "what is this university", "about the university",
                 "about the school", "what is nutm about", "what does nutm do", "whats nutm", "what is this school"}


GENERIC_TOPIC = (r"hear|response|decision|result|status|accept|instal|application fee|scholarship|hostel|accommodation|defer|"
                 r"reapply|transfer|attendance|work while|meal|travel|siwes|jamb|gmat|offer|available|list of|nutm|school fee")
CLARIFY = ("Which programme do you mean? I can help with MSc Data Science, MSc Software Engineering, the MBA, or an "
           "undergraduate B.Sc. programme (Computer Science, Cybersecurity, Information Technology, Accounting, "
           "Business Administration, Entrepreneurship or Economics). For example: \"How much is the MBA?\"")


def detect_prog(text):
    """Which programme is the question about? (a key of PROG_LABEL, or None)"""
    t = text.lower()
    found = [k for k, pat in PROG_PATTERNS if re.search(pat, t)]
    if not found:
        return None
    pg = [k for k in found if k in PG_PREFIX]
    if pg and not re.search(UG_WORDS, t):
        return pg[0]
    degrees = [k for k in found if k.startswith("ug:")]
    if degrees:
        return degrees[0]
    if "ug" in found:
        return "ug"
    return pg[0] if pg else None


def detect_intent(text):
    """What does the question ask about? (fee, admission, eligibility, duration, curriculum, start, or None)"""
    t = text.lower()
    for name, pat in INTENT_PATTERNS:
        if re.search(pat, t):
            return name
    return None


def find_entry(retriever, startswith=None, contains=None):
    for e in retriever.entries:
        low = e["title"].lower()
        if startswith and not low.startswith(startswith.lower()):
            continue
        if contains and contains.lower() not in low:
            continue
        return e
    return None


def route(retriever, prog, intent):
    """Exact answer for a programme + topic pair. Returns (text, anchor_entry) or None."""
    if prog in PG_PREFIX:
        e = find_entry(retriever, startswith=PG_PREFIX[prog] + ":", contains=PG_KEY[intent])
        return (e["body"], e) if e else None
    if prog is None or not prog.startswith("ug"):
        return None
    label = PROG_LABEL[prog]
    degree = prog.startswith("ug:")
    computing = prog in COMPUTING

    def entry(sub):
        return find_entry(retriever, contains=sub)

    if intent == "eligibility":
        e = entry("Entry requirements for undergraduate")
        if not e:
            return None
        if not degree:
            return e["body"], e
        group = entry("Computing degrees, O'Level") if computing else entry("Business and economics degrees, O'Level")
        if not group:
            return None
        return (f"{group['body']}\n\nPlease confirm any further subject requirement for {label} with "
                f"admissions@nutm.edu.ng."), group
    if intent == "fee":
        e = entry("Tuition and accommodation fees")
        if not e:
            return None
        if degree:
            return (f"{label} has the same fees as every NUTM undergraduate programme: tuition is N2 million per academic "
                    f"year, and accommodation only is N750,000 per academic year. Fees cover tuition and accommodation "
                    f"only. Students buy their own course materials, meals, and travel; allowances are not provided."), e
        return e["body"], e
    if intent == "admission":
        e = entry("How do I apply for an undergraduate")
        if not e:
            return None
        return ((f"To apply for {label}: " if degree else "") + e["body"] +
                " There is no application fee. You will need your JAMB slip, an essay of at least 300 words, and scanned "
                "documents, and the interview is held by video conference."), e
    if intent == "duration":
        e = entry("Programme length")
        if not e:
            return None
        if degree:
            return (f"{label} runs for a minimum of four (4) academic sessions, or eight (8) consecutive semesters, "
                    f"for candidates who enter through UTME. All NUTM undergraduate programmes have the same length."), e
        return e["body"], e
    if intent == "curriculum":
        e = entry(label) if degree else entry("Undergraduate programmes: list")
        if not e:
            return None
        text = e["body"]
        if computing:
            f = entry("Key features of the computing programmes")
            if f:
                text += "\n\n" + f["body"]
        return text, e
    if intent == "start":
        e = entry("When will I hear about my application")
        if not e:
            return None
        return ((f"For {label}: " if degree else "") + e["body"] +
                " Apply online at https://nutm.edu.ng/university-degree-programs."), e
    return None


def family(title):
    """pg, ug or gen: which group of programmes an entry is about."""
    if title.startswith(("MSc", "MBA", "Postgraduate")):
        return "pg"
    if title.startswith(("Undergraduate", "B.Sc.")):
        return "ug"
    return "gen"


def sanitize_context(retriever, raw):
    """Keep only safe, known values from a context sent by the browser."""
    ctx = {}
    if not isinstance(raw, dict):
        return ctx
    titles = {e["title"] for e in retriever.entries}
    prog, intent, topic = raw.get("prog"), raw.get("intent"), raw.get("topic")
    if isinstance(prog, str) and prog in PROG_LABEL:
        ctx["prog"] = prog
    if isinstance(intent, str) and intent in INTENT_HINT:
        ctx["intent"] = intent
    if isinstance(topic, str) and topic in titles:
        ctx["topic"] = topic
    shown = raw.get("shown")
    if isinstance(shown, list):
        ctx["shown"] = [x for x in shown if isinstance(x, str) and x in titles][-6:]
    return ctx


def _remember(ctx, prog, intent, title):
    if prog:
        ctx["prog"] = prog
    if intent:
        ctx["intent"] = intent
    elif prog:
        ctx.pop("intent", None)
    if title:
        ctx["topic"] = title
        shown = ctx.setdefault("shown", [])
        if title in shown:
            shown.remove(title)
        shown.append(title)
        del shown[:-6]


def _more(retriever, ctx):
    topic = ctx.get("topic")
    if not topic:
        return "What would you like to know more about? " + R_HELP
    seen = set(ctx.get("shown", []))
    for score, e in retriever.search_all(topic):
        if e["title"] not in seen and score >= MIN_SCORE * 0.8:
            _remember(ctx, None, None, e["title"])
            return "More on this:\n" + e["body"]
    return ("That is everything I have on this topic. You can ask me about fees, admission, entry requirements, "
            "programme length, courses or contacts.")


def answer(retriever, question, context=None):
    """Answer one question. `context` (a dict) is updated so follow-up questions work."""
    question = question[:MAX_QUESTION_CHARS]
    reply = small_talk(question)
    if reply:
        return reply
    ctx = context if isinstance(context, dict) else {}
    cleaned = clean_text(question)
    if cleaned in ABOUT_PHRASES:
        e = find_entry(retriever, startswith="About NUTM")
        if e:
            _remember(ctx, None, None, e["title"])
            return e["body"]
    if re.fullmatch(MORE_RE, cleaned):
        return _more(retriever, ctx)

    q_prog, q_intent = detect_prog(question), detect_intent(question)
    prog, intent = q_prog, q_intent
    cp, ci = ctx.get("prog"), ctx.get("intent")
    words = len(re.findall(WORD_RE, question.lower()))
    followup = words <= 4 or re.match(r"(and|also|what about|how about|what of|then|same for|so|what if|for|the)\b", question.lower().strip())
    if intent and not prog and cp and not re.search(OTHER_TOPIC, question.lower()):
        prog = cp
    elif prog and not intent and ci and followup:
        intent = ci
    elif not prog and not intent and cp and ci and re.search(MODE_RE, question.lower()):
        prog, intent = cp, ci

    search_q = question
    if prog and not q_prog:
        search_q += " " + PROG_LABEL[prog]
    if intent and not q_intent:
        search_q += " " + INTENT_HINT[intent]
    results = retriever.search_all(search_q)

    ql = question.lower()
    if (intent and not prog and words <= 8 and results and results[0][0] >= MIN_SCORE
            and not re.search(OTHER_TOPIC, ql) and not re.search(GENERIC_TOPIC, ql)):
        _remember(ctx, None, intent, None)  # remember the topic so "the MBA" can complete the question
        return CLARIFY

    routed = route(retriever, prog, intent) if (prog and intent) else None
    if routed:
        text, anchor = routed
        top_score, top = results[0] if results else (0.0, None)
        anchor_score = next((sc for sc, e in results if e is anchor), 0.0)
        # keep the exact answer unless a different entry clearly matches the wording much better
        generic = top is not None and (top["title"].startswith("B.Sc.") or "overview" in top["title"].lower()
                                       or family(top["title"]) not in ("gen", "ug" if prog.startswith("ug") else "pg"))
        if top is None or top is anchor or generic or top_score <= anchor_score * 1.3:
            _remember(ctx, prog, intent, anchor["title"])
            return text

    if (not results or results[0][0] < MIN_SCORE) and ctx.get("topic") and words <= 5:
        retry = retriever.search_all(question + " " + ctx["topic"])  # short follow-up: use the earlier topic
        if retry and retry[0][0] >= MIN_SCORE:
            results = retry
    if not results or results[0][0] < MIN_SCORE:
        return FALLBACK
    best_score, best = results[0]
    reply = best["body"]
    if len(results) > 1:
        second_score, second = results[1]
        if second_score >= best_score * SECOND_ANSWER_RATIO and second_score >= MIN_SCORE:
            reply += f"\n\nRelated: {second['title']}\n{second['body']}"
    _remember(ctx, q_prog or (prog if prog != cp else None), intent if (q_intent or prog) else None, best["title"])
    return reply


def main():
    try:  # make the Naira sign print correctly on Windows consoles
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    retriever = Retriever(load_entries(KB_FILE))
    context = {}  # remembers the conversation so follow-up questions work
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
        if clean_text(question) in GOODBYES:
            print("Bot:", R_BYE)
            break
        print("\nBot:", answer(retriever, question, context))


if __name__ == "__main__":
    main()
