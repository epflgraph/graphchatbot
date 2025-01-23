def build_input_field_instructions(fields):
    input_field_instructions = {
        'title': "* The `title` given to the video file of the lecture.",
        'description': "* The `description` given to the video file of the lecture.",
        'keywords': "* The `keywords` the video file is associated with.",
        'slides': "* A list of `slides` in chronological order containing raw text extracted from the lecture slides with OCR. This text can contain many typos and poorly detected characters. Do your best at interpreting this as faithfully as possible.",
        'transcripts': "* A list of `transcripts` in chronological order containing automatically generated subtitles. This text can contain errors and some portions might not be relevant. Do your best at interpreting this as faithfully as possible.",
    }

    input_field_instructions = '\n'.join([input_field_instructions[field] for field in fields])

    return input_field_instructions


def build_output_field_instructions(include_solution):
    output_field_instructions = {
        'statement_en': "* An exercise `statement`, in English, as it would appear in an exam. Make sure the statement is clear, unambiguous and no guessing is required. Match the exercise to the user's `description`.",
        'statement_fr': "* A French translation of `statement_en`.",
        'title_en': "* A `title` for the exercise, in English, limited to 10 words.",
        'title_fr': "* A French translation of `title_en`.",
        'description_en': "* A `description` for the exercise, in English, using between 24 and 32 words, consisting of one sentence in the third person that conveys what the exercise is about, but not disclosing the solution.",
        'description_fr': "* A French translation of `description_en`.",
        'solution_en': "* A clear, step-by-step `solution` for the exercise, in English. This should not just be hints on how to solve the exercise, but rather what would be given the best possible grade in an exam.",
        'solution_fr': "* A French translation of `solution_en`.",
        'tags_en': "* A list of `tags` with the concepts, in English, the exercise is about. Make sure they are all distinct, in lowercase, not acronyms and sorted in descending order of relevance.",
    }

    if not include_solution:
        del output_field_instructions['solution']

    output_field_instructions = '\n'.join(output_field_instructions.values())

    return output_field_instructions


def build_bloom_taxonomy_instructions(bloom_level):
    if bloom_level is None:
        bloom_taxonomy_instructions = ""
    else:
        bloom_taxonomy_actions = {
            1: "Recognize, List, Describe, Identify, Retrieve, Name, Locate, Find",
            2: "Interpret, Exemplify, Classify, Summarise, Compare, Contrast, Explain, Distinguish, Outline, Restate, Translate, Estimate, Differentiate, Identify, Order, Group, Infer, Retell",
            3: "Execute, Implement, Solve, Choose, Modify, Application, Represent (in another format), Use methods, concepts or theories in new situations, Substitute",
            4: "Differentiate, Organise, Attribute, Analyse, Categorise, Divide, Arrange (into smaller components), Separate, Explain, Identify patterns, Recognise hidden meanings, Identify components, Sequence, Change a variable, Identify problems, Identify steps",
            5: "Check, Critique, Validate, Recommend, Hypothesize, Generalise, Predict, Arrange, Propose, Relate (knowledge from different areas), Infer, Justify, Rate, Conclude, Select, Verify",
            6: "Design, Invent, Construct, Devise, Plan, Make, Produce",
        }
        bloom_taxonomy_instructions = f"""
The exercise should be based on skill level {bloom_level} from the revised Bloom's taxonomy, and it should trigger one of the following actions on the user: {bloom_taxonomy_actions[bloom_level]}.
    """

    return bloom_taxonomy_instructions


def build_output_format_instructions(output_format):
    output_format_instructions = {
        'plain-text': """Output the exercise `statement` and `solution` as plain text, without any Markdown nor LaTeX code.""",
        'markdown': """Output the exercise `statement` and `solution` as Markdown text.""",
        'latex': """Output the exercise `statement` and `solution` as LaTeX code, not Markdown.""",
    }

    return output_format_instructions[output_format]


def build_extra_instructions():
    return """Make sure to comply with the following conditions:
* Do not copy exercises from the given input data.
* The exercise should remain in the context of the given material and solved using the same methods.  
* Exercises must be well-defined, complete and solvable with the given information.
* Do not include contact information, such as email addresses, phone numbers, or postal addresses."""


################################################################

def build_text_system_prompt(bloom_level, include_solution, output_format):
    # Bloom taxonomy
    bloom_taxonomy_instructions = build_bloom_taxonomy_instructions(bloom_level)

    # Output fields
    output_field_instructions = build_output_field_instructions(include_solution)

    # Output format
    output_format_instructions = build_output_format_instructions(output_format)

    # Extra instructions
    extra_instructions = build_extra_instructions()

    # Build full system prompt
    system_prompt = f"""
Your task is to generate an academic exercise about some given material `text`. You will be given a piece of `text`, containing some factual information. This can go from a single statement to the entire content of a lecture. In addition, the user will also provide a `description` with precise instructions about the exercise you should generate. 
{bloom_taxonomy_instructions}
Produce the following items:
{output_field_instructions}

{output_format_instructions}

{extra_instructions}
"""

    return system_prompt


def build_lecture_system_prompt(content, bloom_level, include_solution, output_format):
    # Input fields
    fields = content.keys()
    input_field_instructions = build_input_field_instructions(fields)

    # Bloom taxonomy
    bloom_taxonomy_instructions = build_bloom_taxonomy_instructions(bloom_level)

    # Output fields
    output_field_instructions = build_output_field_instructions(include_solution)

    # Output format
    output_format_instructions = build_output_format_instructions(output_format)

    # Extra instructions
    extra_instructions = build_extra_instructions()

    # Build full system prompt
    system_prompt = f"""
Your task is to generate an exercise for a lecture based on the lecture material and a `description`. You will be given raw data of a video lecture, containing the following fields:
{input_field_instructions}

In addition, the user will also provide an `description` with precise details about the exercise you should generate. 
{bloom_taxonomy_instructions}
Produce the following items:
{output_field_instructions}

{output_format_instructions}

{extra_instructions}
"""

    return system_prompt


################################################################

def build_human_prompt(content, description):
    human_prompt = f"""
Here is the input data:
{content}

And this is the user's `description` of the exercise:
> {description}
"""

    return human_prompt

################################################################


if __name__ == '__main__':
    content = {'text': "aaa bbb ccc ddd"}
    description = "ho ho ho"
    system_prompt = build_text_system_prompt(bloom_level=3, include_solution=True, output_format='plain-text')
    human_prompt = build_human_prompt(content, description)

    print(system_prompt)
    print(human_prompt)

    ################################################################

    print('#' * 64)

    ################################################################

    content = {'title': "A", 'description': "B", 'slides': ["aaa", "bbb"], 'transcripts': ["ccc", "ddd"]}
    description = "ho ho ho"
    system_prompt = build_lecture_system_prompt(content=content, bloom_level=3, include_solution=True, output_format='plain-text')
    human_prompt = build_human_prompt(content, description)

    print(system_prompt)
    print(human_prompt)
