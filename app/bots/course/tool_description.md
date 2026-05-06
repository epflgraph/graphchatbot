Searches course material (theory, exercises, exams, etc.) for this EPFL course. Returns matching document chunks.

When processing questions:
1. Identify distinct topics and break down complex questions into information-dense queries.
2. Analyze whether this is a single question or contains multiple sub-questions.
3. Extract keywords focusing on technical terms and course concepts.
4. Apply smart filtering to classify questions accurately.
5. Be thorough — better to search broadly than miss information.

Calling strategy:
- Always make at least one call with key concepts in the query and filters={type:"theory"}. Make additional theory calls if there are multiple concepts or sub-questions.
- If the question is about practice or an exam, make the theory call(s) above AND:
  - One call with query="" using filters only to locate the specific exercise/exam.
  - One call using keywords in the query filtering only by type.
- Make separate tool calls for unrelated topics or sub-questions.
- If an exercise number is followed by a letter (e.g. "exo 4f"), ignore the letter in filters.

Query rules:
- Create concise keyword queries (max 15 words).
- Use technical terminology and course-specific terms.
- query must always be included, either with content or as an empty string (query="").
- Never set a filter field to None. Omit the field entirely if not needed.
- You have exactly one opportunity to make tool calls: REQUEST ALL IN PARALLEL IN ONE SINGLE MESSAGE.
