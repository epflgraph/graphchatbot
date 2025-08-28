from typing import Union

from fastapi import APIRouter

from app.exercises.schemas import GenerateTextExerciseInput, GenerateLectureExerciseInput
import app.exercises as exercises

router = APIRouter()


@router.post('/generate_exercise')
async def generate_exercise(input: Union[GenerateTextExerciseInput, GenerateLectureExerciseInput]):
    """
    Generates an exercise about some given text or lecture.

    Args:
        input (Union[GenerateTextExerciseInput, GenerateLectureExerciseInput]): Input object containing text or lecture_id, a description and some other parameters like the bloom level or whether to include a solution.

    Returns:
        dict: An object containing the different field for the exercise.
    """

    description = input.description
    bloom_level = input.bloom_level
    include_solution = input.include_solution
    output_format = input.output_format
    llm_model = input.llm_model
    openai_api_key = input.openai_api_key

    if isinstance(input, GenerateTextExerciseInput):
        return exercises.generate_text_exercise(input.text, description, bloom_level, include_solution, output_format, llm_model, openai_api_key)
    elif isinstance(input, GenerateLectureExerciseInput):
        return exercises.generate_lecture_exercise(input.lecture_id, description, bloom_level, include_solution, output_format, llm_model, openai_api_key)

    return {}
