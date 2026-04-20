from abc import abstractmethod
from typing import Optional

from langchain.tools import tool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from app.bots.base import Bot, BaseState
from app.bots.nodes.classify import make_classify_node
from app.bots.nodes.model import make_model_node
from app.bots.nodes.tools import make_tools_node
from app.interfaces.graphai import GraphAIClient


class CourseState(BaseState):
    category: Optional[str]
    force_tools: bool


CATEGORIES = {
    'greeting': {
        'description': "The user is just greeting the assistant or similar.",
        'force_tools': False,
    },
    'theory': {
        'description': "The user's request is about a theoretical aspect of the course.",
        'force_tools': True,
    },
    'practice': {
        'description': "The user's request is about an exercise, lab session, practice exam or similar.",
        'force_tools': True,
    },
    'admin': {
        'description': "The user's request is about an administrative aspect of the course, like schedule, rooms, grading, or logistics.",
        'force_tools': False,
    },
    'unrelated': {
        'description': "The user's request is completely unrelated to the course.",
        'force_tools': False,
    },
}

RETRIEVAL_SYSTEM_PROMPT = """\
You are an intelligent assistant for an EPFL course. Your task is to extract search queries for \
retrieval augmented generation (RAG).

When processing questions:
1. Identify distinct topics and break down complex questions into information-dense queries.
2. Analyze whether this is a single question or contains multiple sub-questions.
3. Extract keywords focusing on technical terms and course concepts.
4. Apply smart filtering to classify questions accurately.
5. Be thorough — better to search broadly than miss information.

General tool-calling strategy:
- Always make at least one tool call with key concepts in the query and filters={type:"theory"}. \
Make additional theory calls if there are multiple concepts or sub-questions.
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

Very important:
- You have exactly one opportunity to make tool calls, so REQUEST ALL TOOL CALLS IN PARALLEL \
IN ONE SINGLE MESSAGE."""


class CourseBot(Bot):
    """
    Abstract base for course tutor bots.

    Subclasses must define:
        name: str
        index: str
        groups: list[str]
        tool_input_schema: type[BaseModel]  — ToolInput with course-specific filters
        course_name: str                    — e.g. "MATH-240: Statistics"
        course_details: str                 — full course description for the system prompt

    Subclasses may override:
        CATEGORIES
        pedagogical_instructions: str       — provided by HintingCourseBot / DirectCourseBot
        retrieval_notes: str                — extra instructions appended to retrieval prompt
        system_prompt                       — override entirely if needed
        retrieval_system_prompt             — override entirely if needed
        build_tools()
        build_graph()
    """

    tool_input_schema: type[BaseModel]
    course_name: str
    course_details: str

    CATEGORIES: dict = CATEGORIES

    # --- Prompt slots ---

    @property
    @abstractmethod
    def pedagogical_instructions(self) -> str: ...

    @property
    def retrieval_notes(self) -> str:
        return ""

    @property
    def system_prompt(self) -> str:
        from app.bots.prompts import general_considerations

        parts = [
            f'You are a supportive AI tutor for "{self.course_name}", a course at EPFL. '
            f'Your goal is to help students by providing correct, precise, and concise answers.',
            f'# Course details\n```\n{self.course_details}\n```',
            f'# Pedagogical considerations\n{self.pedagogical_instructions}',
            f'# General considerations\n{self._course_format}\n{general_considerations()}'
            f'\n* For admin questions (schedule, grading, rooms), tell the student to contact the teaching team.'
            f'\n* For questions unrelated to the course, politely explain that you can only help with course-related questions.',
        ]
        return '\n\n'.join(parts)

    @property
    def retrieval_system_prompt(self) -> str:
        notes = self.retrieval_notes
        if notes:
            return RETRIEVAL_SYSTEM_PROMPT + f'\n\n# Course-specific notes\n{notes}'
        return RETRIEVAL_SYSTEM_PROMPT

    _course_format = """\
* Format your answer using Markdown (e.g., math, links, `inline code`, ```code fences```, lists, tables).
* When using Markdown, use backticks for file/directory/function names. Use \\( and \\) for inline math, \\[ and \\] for block math, and avoid math in unicode.
* Always reference source documents which have a `url` field using a Markdown link, with `title` as the link text: [title](url).
* Never reference source documents which do not have a `url` field using a Markdown link.
* Never link to a url that does not come from the source documents."""

    # --- Tools ---

    async def search_course_material(self, query: str, filters) -> list:
        """
        Searches the course material with the given query and filters.
        Returns a list of document chunks that best match the query while satisfying the filters.
        """
        if isinstance(filters, BaseModel):
            filters_dict = filters.model_dump(exclude_none=True)
        elif isinstance(filters, dict):
            filters_dict = {k: v for k, v in filters.items() if v is not None}
        else:
            filters_dict = {}

        print(f"[{self.name.upper()} TOOL]", f"query=`{query}` filters=`{filters_dict}`")

        results = await GraphAIClient().rag_retrieve(index=self.index, texts=[query], filters=filters_dict)

        print(f"[{self.name.upper()} TOOL]", f"Retrieved {len(results)} chunks.")

        return [
            {k: v for k, v in {
                'type': f"{r.get('type')}: {r.get('subtype')}",
                'title': r.get('title'),
                'week': r.get('week'),
                'number': r.get('number'),
                'url': r.get('original_link'),
                'page': r.get('page'),
                'position': r.get('position'),
                'content.fr': r.get('content.fr'),
                'content.en': r.get('content.en'),
                'associated_video_lectures': [
                    {'title': v.get('title'), 'url': v.get('original_link')}
                    for v in r.get('associated_video_lectures', [])
                ] or None,
            }.items() if v is not None}
            for r in results
        ]

    def build_tools(self) -> list:
        return [tool('search_course_material', args_schema=self.tool_input_schema)(self.search_course_material)]

    def build_graph(self) -> CompiledStateGraph:
        tools = self.build_tools()

        workflow = StateGraph(CourseState, context_schema=Bot)
        workflow.add_node('classify', make_classify_node(self.CATEGORIES))
        workflow.add_node('model', make_model_node(tools))
        workflow.add_node('tools', make_tools_node(tools, back_to='model'))
        workflow.set_entry_point('classify')
        workflow.add_edge('classify', 'model')

        return workflow.compile()


class HintingCourseBot(CourseBot):
    """CourseBot variant that uses hint-based, Socratic pedagogical style."""

    @property
    def pedagogical_instructions(self) -> str:
        return """\
The questions you receive typically come from students following the course. They range from conceptual \
questions, proofs, and definitions to computational problems, solutions to exercises or past exam questions, \
and multi-step problem solving. Your answers should be adapted accordingly.

- Required answer format: hint-based guidance (adaptive, natural tone). ALWAYS provide hints first.
- Determine the knowledge gap or misconception and plan one or two hints that help the student \
without revealing the answer.
- Provide one or two progressive hints (more only if necessary). Each hint introduces a new idea.
- Be sure the hints don't provide the final solution.
- If the question is trivial or purely factual, give the direct answer concisely.
- Be friendly and natural, not robotic; go straight to the point.
- Adapt to the student's level (explicit or inferred).
- Ensure strict correctness in mathematical, logical, and conceptual statements.
- Address misconceptions gently; distinguish intuition from formal truth.
- Retrieve the relevant course documents and link to those that provide a url.
- Do not invent sources if none were retrieved.
- If a specific exercise, series, exam, or lecture is not in the retrieved information, \
tell the student you couldn't find it. Do not ask them to provide it.
- If an image doesn't seem to relate to the course material, gently ask for clarification.
- Never answer questions about exam rules, future exam content, grading, or scheduling."""


class DirectCourseBot(CourseBot):
    """CourseBot variant that gives direct, complete answers."""

    @property
    def pedagogical_instructions(self) -> str:
        return """\
You are a helpful and knowledgeable tutor who provides clear, correct, and concise answers. \
When a student asks for help with an exercise, explain the correct solution step-by-step and provide \
any formulas, definitions, or examples they need. Do not ask follow-up questions — just provide the \
most accurate and complete answer possible."""
