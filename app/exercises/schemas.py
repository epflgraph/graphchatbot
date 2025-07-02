from typing import Literal

from pydantic import BaseModel

from langchain.output_parsers import PydanticOutputParser


class GenerateTextExerciseInput(BaseModel):
    text: str
    description: str
    bloom_level: Literal[None, 1, 2, 3, 4, 5, 6] = None
    include_solution: bool = True
    output_format: Literal['plain-text', 'markdown', 'latex'] = 'plain-text'
    llm_model: Literal['gpt-4o-mini', 'gpt-4o'] = 'gpt-4o-mini'
    openai_api_key: str


class GenerateLectureExerciseInput(BaseModel):
    lecture_id: str
    description: str
    bloom_level: Literal[None, 1, 2, 3, 4, 5, 6] = None
    include_solution: bool = True
    output_format: Literal['plain-text', 'markdown', 'latex'] = 'markdown'
    llm_model: Literal['gpt-4o-mini', 'gpt-4o'] = 'gpt-4o-mini'
    openai_api_key: str


class ExerciseWithSolution(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    statement_en: str
    statement_fr: str
    title_en: str
    title_fr: str
    description_en: str
    description_fr: str
    solution_en: str
    solution_fr: str
    tags_en: list[str]


class ExerciseWithoutSolution(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    statement_en: str
    statement_fr: str
    title_en: str
    title_fr: str
    description_en: str
    description_fr: str
    tags_en: list[str]


def build_response_schema(include_solution):
    if include_solution:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "exercise_with_solution",
                "strict": True,
                "schema": ExerciseWithSolution.model_json_schema()
            }
        }
    else:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "exercise_without_solution",
                "strict": True,
                "schema": ExerciseWithoutSolution.model_json_schema()
            }
        }


def parse_response(response, include_solution):
    # Instantiate corresponding parser
    if include_solution:
        parser = PydanticOutputParser(pydantic_object=ExerciseWithSolution)
    else:
        parser = PydanticOutputParser(pydantic_object=ExerciseWithoutSolution)

    return parser.parse(response)
