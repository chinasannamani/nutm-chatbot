# NUTM Assistant

A question-answering chatbot for the **Nigerian University of Technology and Management (NUTM)**. It answers questions about undergraduate and postgraduate programmes, tuition fees, entry requirements, admission steps and contact details, and it can be embedded on any website with a single line of code.

Built for the **Python for Data Science** course as a Python project.

> **Disclaimer:** This is a student project, not an official NUTM product. Its answers come from NUTM public materials collected in October 2026 and may become out of date. Always confirm important details (fees, deadlines, requirements) with NUTM admissions.

**Live demo:** https://YOUR-APP-NAME.onrender.com
**Embedded-on-a-website demo:** https://YOUR-APP-NAME.onrender.com/demo

## What it can answer

- "What postgraduate programmes does NUTM offer?"
- "How much is the MSc Data Science tuition?"
- "How do I apply for the MBA?"
- "What are the entry requirements for undergraduate programmes?"
- "Can I pay my fees in instalments?"
- "Where is the campus and how do I contact admissions?"

If it cannot find a good match, it says so and gives NUTM's contact details instead of guessing.

## How it works

1. **Knowledge base:** `nutm_knowledge_base.txt` holds about 77 short entries written from the NUTM website, the MSc Data Science, MSc Software Engineering and MBA brochures, and the undergraduate FAQ.
2. **Retrieval:** each entry and each question is turned into a TF-IDF word vector (with simple stemming, synonyms and programme detection, so "how much is the MBA" finds the MBA fee entry). The entry with the highest cosine similarity is returned as the answer.
3. **Web interface:** a Python web server (`nutm_server.py`) exposes a `/chat` endpoint. A JavaScript widget (`widget.js`) provides the chat bubble, with minimize and close buttons.

There is no large language model and no API key. The chatbot only returns text that exists in the knowledge base, so it does not make things up. In RAG terms, this project implements the retrieval step only.

## Project files

| File | Purpose |
|---|---|
| `nutm_chatbot.py` | The chatbot engine and a terminal chat. Run it directly for a text-only version. |
| `nutm_server.py` | Web server with the `/chat` endpoint; also serves the pages and widget. |
| `nutm_knowledge_base.txt` | The knowledge base (edit this to change what the bot knows). |
| `widget.js` | Embeddable chat widget (bubble, minimize and close buttons). |
| `chat.html` | Full-page chatbot. |
| `demo_site.html` | Mock NUTM homepage showing the widget embedded. |
| `nutm_logo.png`, `nutm_icon.png` | NUTM logo images used by the interface. |
| `requirements.txt` | Empty on purpose: no third-party packages are needed. |

## Run it on your computer

Requirements: **Python 3.8 or newer**. No pip installs and no virtual environment are needed.

```bash
python nutm_server.py
```

Your browser opens automatically. If not, go to:

- `http://localhost:8000/` for the full-page chatbot
- `http://localhost:8000/demo` for the mock NUTM website with the chat bubble

For a text-only version in the terminal:

```bash
python nutm_chatbot.py
```

Keep all the files in the same folder.

## Embed it on a website

After the chatbot is hosted at a public address, add one line before the closing `</body>` tag of any page:

```html
<script src="https://YOUR-APP-NAME.onrender.com/widget.js"></script>
```

Add `data-open="true"` to the script tag to start with the chat window open.

## Deploy online (Render, free plan)

1. Push these files to a GitHub repository.
2. On [render.com](https://render.com), choose **New + → Web Service** and select the repository.
3. Use these settings:
   - Language: **Python 3**
   - Build command: `pip install -r requirements.txt`
   - Start command: `python nutm_server.py`
   - Instance type: **Free**
4. Deploy. Render gives you a public link, which you can turn into a QR code for sharing.

The server reads the `PORT` variable that the host provides and listens on all network interfaces automatically.

## Update or extend the knowledge base

Open `nutm_knowledge_base.txt` and add an entry in this format:

```
### Short title of the entry
keywords: words, people, might, use, when, asking
The answer text the chatbot should reply with.
```

Keywords are not shown to users. They help the bot match different wordings of the same question. Restart the server after editing.

## Limitations

- It matches words, not meaning. Very unusual phrasings may miss the right entry.
- It answers one question at a time and does not remember earlier messages.
- Some NUTM sources disagree (for example, programme start dates differ between the website and an older brochure). Where this happens, the knowledge base mentions both.
- Information was collected in October 2026 and must be refreshed by hand when NUTM updates its materials.
- The free hosting plan sleeps after about 15 minutes of inactivity.

## Possible improvements

- Semantic search with sentence embeddings for better understanding of rephrased questions
- A language model to turn retrieved passages into natural answers (full RAG)
- Conversation memory for follow-up questions
- A Telegram bot using the same engine
- An automatic scraper that refreshes the knowledge base from nutm.edu.ng

## Data sources

- NUTM website (nutm.edu.ng): home, about, academics, undergraduate, postgraduate, executive education and career pages
- NUTM MSc Data Science, MSc Software Engineering and 2026 MBA programme brochures
- NUTM undergraduate FAQ page

NUTM names, logos and content belong to the Nigerian University of Technology and Management.

## Author

Chinasa Priscilla Emeji, MSc Data Science, Nigerian University of Technology and Management.
Course: Python for Data Science.
