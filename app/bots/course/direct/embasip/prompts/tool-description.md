Searches the knowledge base of the EPFL EMBA Strategic & Innovative Project (SIP). Returns matching document chunks.

The knowledge base contains only `theory` documents, in two subtypes:
- `corpus`: 109 knowledge cards answering the questions participants ask about their SIP — the research process (K, 91 cards), admin and practicalities (A, 15 cards), and evaluation (E, 3 cards). Each card stands alone.
- `sources`: raw, original source documents the cards rest on. Depending on the license, they contain either the full text or, for copyrighted sources, a few short passages.

When processing questions:
1. Identify distinct topics and break down complex questions into information-dense queries.
2. Analyze whether this is a single question or contains multiple sub-questions.
3. Extract keywords focusing on research methodology and program terms.
4. Be thorough — better to search broadly than miss information.

Calling strategy:
- Always make at least one call with key concepts in the query and filters={type:"theory"} (subtype omitted, so both subtypes are searched).
- For questions about rules, deadlines, supervision, confidentiality, academic integrity, grading, or the defense, make a call whose query names the concrete topic (e.g. "confidentiality agreement", "defense jury criteria"); the A and E cards hold these answers.
- For methodology questions (problem statement, literature, approach, data collection and analysis, writing), add a call with subtype "corpus".
- To ground an answer in the original documents (quotes, full references), add a call with subtype "sources".
- Make separate calls for unrelated topics or sub-questions.

Query rules:
- Create concise keyword queries (max 15 words).
- Use the terminology of the cards (e.g. "research question", "literature review", "defense").
- query must always be included, either with content or as an empty string (query="").
- Never set a filter field to None. Omit the field entirely if not needed.
- You have exactly one opportunity to make tool calls: REQUEST ALL IN PARALLEL IN ONE SINGLE MESSAGE.
