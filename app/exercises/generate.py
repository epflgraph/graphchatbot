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
    build_text_system_prompt,
    build_lecture_system_prompt,
    build_human_prompt,
)
from app.exercises.schemas import (
    build_response_schema,
    parse_response,
)

from app.config import config


def call_llm(model_name, system_prompt, human_prompt, include_solution):
    ################################################################
    # Send request to LLM                                          #
    ################################################################

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
            print('[GENERATE EXERCISE]', msg)
            return {'error': msg}
        except Exception as e:
            msg = f"There was an error when calling the LLM provider: {e}"
            print('[GENERATE EXERCISE]', msg)
            return {'error': msg}

    # Parse the structured output
    try:
        exercise = parse_response(output.content, include_solution)
    except Exception as e:
        msg = f"There was an error parsing the LLM's response: {output.content}"
        print('[GENERATE EXERCISE]', msg)
        return {'error': msg}

    # Return if empty response
    if not exercise:
        msg = "The response from the LLM is empty"
        print('[GENERATE EXERCISE]', msg)
        return {'error': msg}

    print('[GENERATE EXERCISE]', f"Generated exercise: `{exercise.statement_en[:200]}`")

    # Prepare response object
    response = {
        'exercise': exercise.model_dump(),
        'input_tokens': cb.prompt_tokens,
        'output_tokens': cb.completion_tokens,
        'cost_usd': cb.total_cost,
    }

    return response


def generate_text_exercise(text, description, bloom_level, include_solution, output_format, model_name):
    print('[GENERATE EXERCISE]', f"Generating exercise for text `{text[:100]}` with description `{description[:100]}`")

    # Build system prompt and human prompt
    content = {'text': text}
    system_prompt = build_text_system_prompt(bloom_level=bloom_level, include_solution=include_solution, output_format=output_format)
    human_prompt = build_human_prompt(content=content, description=description)

    # Call LLM to generate exercise
    response = call_llm(model_name, system_prompt, human_prompt, include_solution)

    return response


def fetch_lecture_content(lecture_id, bloom_level, include_solution, output_format):
    ################################################################
    # Fetch lecture data                                           #
    ################################################################

    metadata = fetch_lecture_metadata(lecture_id)
    slides = fetch_lecture_slides(lecture_id)
    transcripts = fetch_lecture_transcripts(lecture_id)

    if not slides and not transcripts:
        msg = f"Not enough slides nor transcripts for lecture {lecture_id}"
        print('[GENERATE EXERCISE]', msg)
        return {'error': msg}

    ################################################################
    # Prune slides and transcripts                                 #
    ################################################################

    # Build lecture content object
    content = {**metadata, 'slides': slides, 'transcripts': transcripts}
    content = {k: v for k, v in content.items() if v}

    # Build system prompt
    system_prompt = build_lecture_system_prompt(content, bloom_level=bloom_level, include_solution=include_solution, output_format=output_format)

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

    print('[GENERATE EXERCISE]', f"Pruned input data, kept {n_slides}/{n_slides_before_pruning} slides ({slide_tokens} tokens) and {n_transcripts}/{n_transcripts_before_pruning} transcripts ({transcript_tokens} tokens)")

    # Skip if not enough input data
    min_n_slides = 6
    min_n_transcripts = 6
    if n_slides < min_n_slides and n_transcripts < min_n_transcripts:
        msg = f"Not enough (sufficiently different) slides ({n_slides}/{min_n_slides}) nor transcripts ({n_transcripts}/{min_n_transcripts})"
        print('[GENERATE EXERCISE]', msg)
        return {'error': msg}

    # Rebuild content after pruning
    # We do this because the content types might have changed after pruning (e.g. slides eat up all tokens and there is no room for transcripts)
    content = {**metadata, 'slides': slides, 'transcripts': transcripts}
    content = {k: v for k, v in content.items() if v}

    return content


def generate_lecture_exercise(lecture_id, description, bloom_level, include_solution, output_format, model_name):
    print('[GENERATE EXERCISE]', f"Generating exercise for lecture {lecture_id}: `{description[:100]}`")

    # Build lecture content
    content = fetch_lecture_content(lecture_id, bloom_level, include_solution, output_format)

    # Build system prompt and human prompt
    system_prompt = build_lecture_system_prompt(content, bloom_level=bloom_level, include_solution=include_solution, output_format=output_format)
    human_prompt = build_human_prompt(content, description)

    # Call LLM to generate exercise
    response = call_llm(model_name, system_prompt, human_prompt, include_solution)

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
    text = """
Second law

The change of motion of an object is proportional to the force impressed; and is made in the direction of the straight line in which the force is impressed.[15]: 114 

By "motion", Newton meant the quantity now called momentum, which depends upon the amount of matter contained in a body, the speed at which that body is moving, and the direction in which it is moving.[21] In modern notation, the momentum of a body is the product of its mass and its velocity: p = m v , {\displaystyle \mathbf {p} =m\mathbf {v} \,,} where all three quantities can change over time. Newton's second law, in modern form, states that the time derivative of the momentum is the force: F = d p d t . {\displaystyle \mathbf {F} ={\frac {d\mathbf {p} }{dt}}\,.} If the mass m {\displaystyle m} does not change with time, then the derivative acts only upon the velocity, and so the force equals the product of the mass and the time derivative of the velocity, which is the acceleration:[22] F = m d v d t = m a . {\displaystyle \mathbf {F} =m{\frac {d\mathbf {v} }{dt}}=m\mathbf {a} \,.} As the acceleration is the second derivative of position with respect to time, this can also be written F = m d 2 s d t 2 . {\displaystyle \mathbf {F} =m{\frac {d^{2}\mathbf {s} }{dt^{2}}}.}
A free body diagram for a block on an inclined plane, illustrating the normal force perpendicular to the plane (N), the downward force of gravity (mg), and a force f along the direction of the plane that could be applied, for example, by friction or a string

The forces acting on a body add as vectors, and so the total force on a body depends upon both the magnitudes and the directions of the individual forces.[23]: 58  When the net force on a body is equal to zero, then by Newton's second law, the body does not accelerate, and it is said to be in mechanical equilibrium. A state of mechanical equilibrium is stable if, when the position of the body is changed slightly, the body remains near that equilibrium. Otherwise, the equilibrium is unstable.[15]: 121 [23]: 174 

A common visual representation of forces acting in concert is the free body diagram, which schematically portrays a body of interest and the forces applied to it by outside influences.[24] For example, a free body diagram of a block sitting upon an inclined plane can illustrate the combination of gravitational force, "normal" force, friction, and string tension.[note 4]

Newton's second law is sometimes presented as a definition of force, i.e., a force is that which exists when an inertial observer sees a body accelerating. In order for this to be more than a tautology — acceleration implies force, force implies acceleration — some other statement about force must also be made. For example, an equation detailing the force might be specified, like Newton's law of universal gravitation. By inserting such an expression for F {\displaystyle \mathbf {F} } into Newton's second law, an equation with predictive power can be written.[note 5] Newton's second law has also been regarded as setting out a research program for physics, establishing that important goals of the subject are to identify the forces present in nature and to catalogue the constituents of matter.[15]: 134 [26]: 12-2 
"""
    description = "An exercise involving an inclined plane, without friction."

    bloom_level = 5
    include_solution = True
    model_name = 'gpt-4o-mini'

    result = generate_text_exercise(text, description, bloom_level=bloom_level, include_solution=include_solution, output_format='latex', model_name=model_name)

    print(result)


# if __name__ == '__main__':
#     lecture_id = '0_92916guq'
#     description = r"An exercise to compute the volume of a sphere cap of angle $\alpha$ using spherical coordinates."
#     # description = r"An exercise to compute the volume of a torus."
#     # description = r"An exercise to compute the volume of the Pokémon Snorlax, decomposing it into its head and body (spheres), hands and feet (short cylinders) and ears (cones)."
#
#     # lecture_id = '0_qf0m3zhf'
#     # description = r"An exercise about the evolution of the population of rabbits and wolves."
#     # description = r"An exercise with a concrete example of a 2D dynamical system that has three or more equilibrium points."
#     # description = r"An exercise where the populations of the three Pokémon starters evolve according to their type advantages."
#
#     # lecture_id = '0_3tnuqgj7'
#     # # description = r"An exercise with three charges"
#     # # description = r"An exercise involving an electric field that disappears instantly after some time."
#     # description = r"An exercise where Pikachu uses Thunderbolt on four Spearows."
#
#     ################################################################
#
#     include_solution = True
#
#     result = generate_lecture_exercise(lecture_id, description, include_solution)
#
#     ################################################################
#
#     latex_str = build_latex_mockup(result['exercise'], description)
#
#     print(latex_str)
