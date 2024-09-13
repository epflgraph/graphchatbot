from pydantic import BaseModel

from langchain.output_parsers import PydanticOutputParser


class ExerciseWithSolution(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    statement: str
    title: str
    description: str
    solution: str
    tags: list[str]


class ExerciseWithoutSolution(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    statement: str
    title: str
    description: str
    tags: list[str]


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
