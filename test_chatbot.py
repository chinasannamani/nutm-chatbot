"""
Accuracy test for the NUTM chatbot (run:  python test_chatbot.py).
Checks that questions return the right knowledge-base entry (top-1 and top-3)
and that unrelated questions get the safe 'I could not find that' fallback.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import nutm_chatbot as bot

# (question, text that must appear in the title of the right entry)
IN_SCOPE = [
    ("How much is the MSc Data Science tuition?", "MSc Data Science: tuition"),
    ("what is the fee for software engineering", "MSc Software Engineering: tuition"),
    ("MBA tuition", "MBA: tuition"),
    ("undergraduate tuition fees", "Tuition and accommodation"),
    ("how do I apply for the MBA", "MBA: admission"),
    ("how do I apply for data science masters", "MSc Data Science: admission"),
    ("admission process for software engineering", "MSc Software Engineering: admission"),
    ("entry requirements for undergraduate", "Entry requirements for undergraduate"),
    ("what do I need to study MSc data science", "MSc Data Science: eligibility"),
    ("who can apply for the MBA", "MBA: eligibility"),
    ("can I defer my admission", "defer"),
    ("is NUTM accredited", "accredit"),
    ("where is NUTM located", "contact details"),
    ("how can I contact admissions", "contact details"),
    ("what courses are in MSc data science", "MSc Data Science: curriculum"),
    ("software engineering curriculum", "MSc Software Engineering: curriculum"),
    ("how long is the part time MBA", "MBA: duration"),
    ("how long is the data science program", "MSc Data Science: duration"),
    ("can I pay in installments", "instalments"),
    ("are there scholarships", "Scholarships"),
    ("do I need GRE or GMAT", "GMAT"),
    ("can I switch from part-time to full-time", "switch"),
    ("who is the dean", "leadership"),
    ("what undergraduate programmes are offered", "Undergraduate programmes: list"),
    ("tell me about cybersecurity degree", "Cybersecurity"),
    ("executive education courses", "Executive Education"),
    ("does NUTM have hostels", "accommodation"),
    ("what is the minimum JAMB score", "Entry requirements for undergraduate"),
    ("is there an application fee", "application fee"),
    ("how long is the undergraduate degree", "Programme length"),
    ("do I have to attend campus for part time", "Immersive"),
    ("who are the lecturers", "faculty"),
    ("what partners does NUTM have", "partners"),
    ("do graduates get jobs", "alumni"),
    ("when does data science start", "start date"),
    ("what is SIWES", "SIWES"),
    ("can I work while studying", "work while"),
    ("what is the vision of NUTM", "vision"),
    ("are meals provided", "Meals"),
    ("can I transfer from another university", "Transfers"),
    # TEDLab
    ("what is TEDLab", "What is TEDLab"),
    ("is tedlab a course", "TEDLab"),
    ("how many startups came out of TEDLab", "TEDLab results"),
    ("what is shadow a leader", "Shadow a Leader"),
    ("what is the NUTM scholars program", "Scholars Program"),
    # spelling mistakes
    ("dta science fees", "MSc Data Science: tuition"),
    ("tuiton for the mba", "MBA: tuition"),
]
OFF_TOPIC = ["who won the world cup", "recipe for jollof rice", "what is the weather in Lagos",
    "tell me a joke", "who is the president of Nigeria", "how do I learn to play guitar",
    "bitcoin price today", "what is the capital of France", "how to fix my laptop",
    "best phone to buy", "what time is it", "do you like football"]

SMALL_TALK_TESTS = ["Hello", "hi", "Hi there!", "good morning", "how are you", "what is your name?", "who are you",
    "who made you", "are you a robot", "help", "what can you do", "thanks", "thank you so much", "bye", "ok"]
MIXED = [("hello, how much is the MBA?", "8,000,000"), ("hi what is TEDLab", "capstone")]


# ---- programme x topic matrix: every programme must give the right kind of answer ----
PG = {  # key: (names people use, markers per topic)
    "MSc Data Science": (["MSc Data Science", "data science", "the data science masters"],
        {"fee": "5,000,000", "eligibility": "any field", "admission": "online application", "duration": "18 months",
         "curriculum": "Introduction to Data Science", "start": "September 2026"}),
    "MSc Software Engineering": (["MSc Software Engineering", "software engineering"],
        {"fee": "5,000,000", "eligibility": "software engineering", "admission": "online application", "duration": "18 months",
         "curriculum": "Software Testing", "start": "September 2026"}),
    "MBA": (["the MBA", "MBA"],
        {"fee": "8,000,000", "eligibility": "bachelor", "admission": "online application", "duration": "18 months",
         "curriculum": "Corporate Strategy", "start": "September 2026"}),
}
UG_DEGREES = {  # name -> (is computing, what the description mentions)
    "BSc Accounting": (False, "financial reporting"), "B.Sc. Economics": (False, "microeconomics"),
    "BSc Computer Science": (True, "algorithms"), "BSc Cybersecurity": (True, "cyber-attacks"),
    "BSc Information Technology": (True, "computing infrastructure"),
    "BSc Business Administration": (False, "management strategy"), "BSc Entrepreneurship": (False, "venture"),
}
TEMPLATES = {
    "fee": ["How much is {p}?", "what is the tuition for {p}", "{p} fees"],
    "eligibility": ["entry requirements for {p}", "what do I need to study {p}", "requirements for {p}"],
    "admission": ["how do I apply for {p}", "admission process for {p}"],
    "duration": ["how long is {p}", "duration of {p}"],
    "curriculum": ["what courses are in {p}", "{p} curriculum"],
    "start": ["when does {p} start"],
}


def matrix_cases():
    for label, (names, marks) in PG.items():
        for n in names:
            for topic, mark in marks.items():
                for tpl in TEMPLATES[topic]:
                    yield tpl.format(p=n), mark, label, topic
    for n, (computing, desc) in UG_DEGREES.items():
        marks = {"fee": "N2 million" if computing else "confirm it with admissions", "eligibility": "180",
                 "admission": "university-degree-programs", "duration": "four" if computing else "confirm it with admissions",
                 "curriculum": desc, "start": "rolling basis"}
        for topic, mark in marks.items():
            for tpl in TEMPLATES[topic]:
                yield tpl.format(p=n), mark, n, topic
    g = {"fee": "N2 million", "eligibility": "180", "admission": "university-degree-programs", "duration": "four",
         "curriculum": "Computer Science", "start": "rolling basis"}
    for topic, mark in g.items():
        for tpl in TEMPLATES[topic]:
            yield tpl.format(p="undergraduate programmes"), mark, "undergraduate", topic


FOLLOW_UPS = [  # (conversation, text the LAST reply must contain)
    (["How much is the MBA?", "what about data science?"], "5,000,000"),
    (["How much is the MBA?", "what about data science?", "and software engineering?"], "Software Engineering tuition"),
    (["entry requirements for BSc Accounting", "how much is it?"], "B.Sc. Accounting"),
    (["tell me about MSc software engineering", "how long is it?"], "18 months"),
    (["how do I apply for the MBA", "what about software engineering?"], "Software Engineering admission"),
    (["how much is the MBA", "how do I apply?"], "MBA admission"),
    (["what is TEDLab", "tell me more"], "More on this"),
    (["how much is the MBA?", "thanks", "and data science?"], "MSc Data Science tuition"),
    (["who is the dean", "how much is the MBA"], "8,000,000"),
    (["data science fees", "what are the requirements?"], "any field"),
    (["MBA duration", "what about part-time?"], "Part-Time MBA"),
    (["how much is cybersecurity?", "how long is it?"], "four"),
    (["how much is the fee?", "MBA"], "8,000,000"),
    (["how do I apply?", "undergraduate"], "university-degree-programs"),
    (["how long is it?"], "Which programme"),
    (["who teaches the courses"], "aculty"),
    (["is the university approved by the government"], "NUC"),
    (["what about the MBA?"], ""),  # no earlier question: must still reply sensibly
]
WEIRD = ["", "   ", "????", "\U0001F600", "1234567890", "a" * 1000, "<script>alert(1)</script>", "'; DROP TABLE x;--",
         "\u00f1and\u00fa", "\u4f60\u597d", "HELLO", "MBA", "mba", "Mba fees?", "fees", "apply", "requirements", "contact",
         "NUTM", "nutm?", ".", "...", "-", "tell me a story", "what about the part time?", "and?", "more", "why?",
         "!!!", "ok ok ok ok ok", "thanks thanks", "\n\n", "hello\nhow much is the MBA", "HOW MUCH IS THE MBA??!!"]
SMALL_VARIANTS = ["good mormning", "Good Afternoon!", "good evenin", "goodnight", "good night sir", "okay", "ok", "okey", "welldone",
                  "well done!", "good job", "nice one", "thanks", "thank you very much", "tanks", "bye", "see you", "how far",
                  "wassup", "hello there", "hi nutm", "hy", "helo", "thankyou", "ok thanks", "alright", "noted", "cool",
                  "that is all", "no", "yes", "sorry", "lol", "wow", "you are great", "who r you"]


def extra_checks(r):
    bad = 0
    cases = list(matrix_cases())
    for q, mark, who, topic in cases:
        a = bot.answer(r, q)
        if mark.lower() not in a.lower():
            bad += 1
            print(f"  MATRIX MISS  {q!r}: wanted {mark!r}, got {a[:70]!r}")
    print(f"Programme x topic answers : {len(cases)-bad}/{len(cases)} correct")
    bad = 0
    for convo, want in FOLLOW_UPS:
        ctx = {}
        reply = ""
        for q in convo:
            reply = bot.answer(r, q, ctx)
        if want.lower() not in reply.lower() or not reply.strip():
            bad += 1
            print(f"  FOLLOW-UP MISS {convo}: wanted {want!r}, got {reply[:70]!r}")
    print(f"Follow-up conversations    : {len(FOLLOW_UPS)-bad}/{len(FOLLOW_UPS)} correct")
    bad = 0
    for q in WEIRD:
        try:
            a = bot.answer(r, q, {})
            if not isinstance(a, str) or not a.strip():
                raise ValueError("empty reply")
        except Exception as exc:
            bad += 1
            print(f"  ODD INPUT FAILED {q[:30]!r}: {type(exc).__name__}: {exc}")
    print(f"Odd inputs handled         : {len(WEIRD)-bad}/{len(WEIRD)}")
    bad = [q for q in SMALL_VARIANTS if bot.answer(r, q) == bot.FALLBACK or "could not find" in bot.answer(r, q)]
    for q in bad:
        print(f"  NO FRIENDLY REPLY {q!r}")
    print(f"Small-talk variants        : {len(SMALL_VARIANTS)-len(bad)}/{len(SMALL_VARIANTS)}")
    ctx = bot.sanitize_context(r, {"prog": "<script>", "intent": {"x": 1}, "topic": "nope", "shown": ["a"] * 50})
    print("Untrusted context cleaned  :", "OK" if ctx == {"shown": []} else f"FAILED {ctx}")


def main():
    r = bot.Retriever(bot.load_entries(bot.KB_FILE))
    top1 = top3 = 0
    for q, want in IN_SCOPE:
        titles = [e["title"].lower() for _, e in r.search(q, top_k=3)]
        ok1 = want.lower() in titles[0]
        top1 += ok1
        top3 += any(want.lower() in t for t in titles)
        if not ok1:
            print(f"  MISS  {q!r}\n        wanted '{want}', got {titles[0][:60]!r}")
    n = len(IN_SCOPE)
    print(f"\nIn-scope questions : top-1 {top1}/{n} ({100*top1//n}%)   top-3 {top3}/{n} ({100*top3//n}%)")
    bad = [q for q in OFF_TOPIC if bot.answer(r, q) != bot.FALLBACK]
    for q in bad:
        print(f"  WRONG ANSWER to off-topic question: {q!r}")
    print(f"Off-topic questions: correct fallback {len(OFF_TOPIC)-len(bad)}/{len(OFF_TOPIC)}")
    chatty = [q for q in SMALL_TALK_TESTS if bot.answer(r, q) == bot.FALLBACK]
    for q in chatty:
        print(f"  NO FRIENDLY REPLY to: {q!r}")
    print(f"Greetings and small talk: friendly reply {len(SMALL_TALK_TESTS)-len(chatty)}/{len(SMALL_TALK_TESTS)}")
    mixed = [q for q, word in MIXED if word not in bot.answer(r, q)]
    for q in mixed:
        print(f"  GREETING SWALLOWED THE QUESTION: {q!r}")
    print(f"Greeting + question: answered {len(MIXED)-len(mixed)}/{len(MIXED)}")
    extra_checks(r)

if __name__ == "__main__":
    main()
