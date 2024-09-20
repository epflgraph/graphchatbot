import openai

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)
from langchain_openai import ChatOpenAI
from langchain_community.callbacks import get_openai_callback

from app.exercises.content import (
    fetch_lecture_metadata,
    fetch_lecture_slides,
    fetch_lecture_transcripts,
    count_tokens,
    prune_content,
)
from app.exercises.prompt import (
    build_system_prompt,
    build_human_prompt,
)
from app.exercises.schemas import (
    build_response_schema,
    parse_response,
)

from app.config import config


def generate_lecture_exercise(lecture_id, description, include_solution):
    model_name = 'gpt-4o-mini'

    print('[LECTURE EXERCISE]', f"Generating exercise for lecture {lecture_id}: `{description[:100]}`")

    ################################################################
    # Fetch lecture data                                           #
    ################################################################

    metadata = fetch_lecture_metadata(lecture_id)
    slides = fetch_lecture_slides(lecture_id)
    transcripts = fetch_lecture_transcripts(lecture_id)

    if not slides and not transcripts:
        msg = f"Not enough slides nor transcripts for lecture {lecture_id}"
        print('[LECTURE EXERCISE]', msg)
        return {'error': msg}

    ################################################################
    # Prune slides and transcripts                                 #
    ################################################################

    # Build lecture content object
    content = {**metadata, 'slides': slides, 'transcripts': transcripts}
    content = {k: v for k, v in content.items() if v}

    # Build system prompt
    system_prompt = build_system_prompt(content, include_solution=include_solution)

    # Prune input until it fits the model's context window.
    # We do this in two steps:
    #   * We first prune only the slides
    #   * We then prune the transcripts with the remaining context window size
    # We do it like this to prioritise slides, because there are typically less than transcripts and arguably contain more meaningful information than transcripts

    # Token padding is the sum of the system prompt, metadata and output, plus some wiggle room due to tiktoken's unprecise count
    max_output_tokens = 5000
    system_tokens = count_tokens(system_prompt, model_name)
    metadata_tokens = count_tokens(metadata, model_name)
    token_padding = system_tokens + metadata_tokens + max_output_tokens

    # Slides
    n_slides_before_pruning = len(slides)
    slides = prune_content(slides, model_name, token_padding=token_padding)
    slide_tokens = count_tokens(slides, model_name)
    token_padding += slide_tokens
    n_slides = len(slides)

    # Transcripts
    n_transcripts_before_pruning = len(transcripts)
    transcripts = prune_content(transcripts, model_name, token_padding=token_padding)
    transcript_tokens = count_tokens(transcripts, model_name)
    token_padding += transcript_tokens
    n_transcripts = len(transcripts)

    print('[LECTURE EXERCISE]', f"Pruned input data, kept {n_slides}/{n_slides_before_pruning} slides ({slide_tokens} tokens) and {n_transcripts}/{n_transcripts_before_pruning} transcripts ({transcript_tokens} tokens)")

    # Skip if not enough input data
    min_n_slides = 6
    min_n_transcripts = 6
    if n_slides < min_n_slides and n_transcripts < min_n_transcripts:
        msg = f"Not enough (sufficiently different) slides ({n_slides}/{min_n_slides}) nor transcripts ({n_transcripts}/{min_n_transcripts})"
        print('[LECTURE EXERCISE]', msg)
        return {'error': msg}

    ################################################################
    # Send request to LLM                                          #
    ################################################################

    # Rebuild content after pruning
    # We do this because the content types might have changed after pruning (e.g. slides eat up all tokens and there is no room for transcripts)
    content = {**metadata, 'slides': slides, 'transcripts': transcripts}
    content = {k: v for k, v in content.items() if v}

    # Rebuild system prompt and build human prompt with pruned content
    system_prompt = build_system_prompt(content, include_solution)
    human_prompt = build_human_prompt(content, description)

    # Gather the messages for the LLM input
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    # Instantiate model
    response_schema = build_response_schema(include_solution)
    model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=60).bind(response_format=response_schema)

    # Send request to LLM
    with get_openai_callback() as cb:
        try:
            output = model.invoke(input=messages)
        except openai.BadRequestError as e:
            msg = f"The LLM provider refused to process the request: {e}"
            print('[LECTURE EXERCISE]', msg)
            return {'error': msg}
        except Exception as e:
            msg = f"There was an error when calling the LLM provider: {e}"
            print('[LECTURE EXERCISE]', msg)
            return {'error': msg}

    # Parse the structured output
    try:
        exercise = parse_response(output.content, include_solution)
    except Exception as e:
        msg = f"There was an error parsing the LLM's response: {output.content}"
        print('[LECTURE EXERCISE]', msg)
        return {'error': msg}

    # Return if empty response
    if not exercise:
        msg = "The response from the LLM is empty"
        print('[LECTURE EXERCISE]', msg)
        return {'error': msg}

    print('[LECTURE EXERCISE]', f"Generated exercise: `{exercise.statement_en[:200]}`")

    # Prepare response object
    response = {
        'lecture_id': lecture_id,
        'exercise': exercise.dict(),
        'n_slides': n_slides,
        'n_transcripts': n_transcripts,
        'input_tokens': cb.prompt_tokens,
        'output_tokens': cb.completion_tokens,
        'cost_usd': cb.total_cost,
    }

    return response


def build_latex_mockup(exercise, description):
    title = exercise['title_en']
    statement = exercise['statement_en']
    gen_description = exercise['description_en']
    solution = exercise['solution_en']
    tags = exercise['tags_en'][:3]

    return rf"""
    \section*{{{title}}}

    \emph{{"{description}"}}

    \vspace{{1em}}

    \noindent
    \framebox{{
        \parbox{{\dimexpr\linewidth-2\fboxsep\relax}}{{\small {gen_description}}}
    }}

    \noindent
    \framebox{{\small {tags[0]}}}
    \framebox{{\small {tags[1]}}}
    \framebox{{\small {tags[2]}}}

    \vspace{{1em}}

    \noindent
    \textbf{{Statement:}} {statement}

    \noindent
    \textbf{{Solution:}} {solution}
    """


if __name__ == '__main__':
    lecture_id = '0_92916guq'
    description = r"An exercise to compute the volume of a sphere cap of angle $\alpha$ using spherical coordinates."
    # description = r"An exercise to compute the volume of a torus."
    # description = r"An exercise to compute the volume of the Pokémon Snorlax, decomposing it into its head and body (spheres), hands and feet (short cylinders) and ears (cones)."

    # lecture_id = '0_qf0m3zhf'
    # description = r"An exercise about the evolution of the population of rabbits and wolves."
    # description = r"An exercise with a concrete example of a 2D dynamical system that has three or more equilibrium points."
    # description = r"An exercise where the populations of the three Pokémon starters evolve according to their type advantages."

    # lecture_id = '0_3tnuqgj7'
    # # description = r"An exercise with three charges"
    # # description = r"An exercise involving an electric field that disappears instantly after some time."
    # description = r"An exercise where Pikachu uses Thunderbolt on four Spearows."

    ################################################################

    include_solution = True

    result = generate_lecture_exercise(lecture_id, description, include_solution)

    ################################################################

    latex_str = build_latex_mockup(result['exercise'], description)

    print(latex_str)
