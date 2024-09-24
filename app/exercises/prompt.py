def build_system_prompt(content, include_solution):
    # Descriptions of input fields
    input_field_descriptions = {
        'title': "* The `title` given to the video file of the lecture.",
        'description': "* The `description` given to the video file of the lecture.",
        'keywords': "* The `keywords` the video file is associated with.",
        'slides': "* A list of `slides` in chronological order containing raw text extracted from the lecture slides with OCR. This text can contain many typos and poorly detected characters. Do your best at interpreting this as faithfully as possible.",
        'transcripts': "* A list of `transcripts` in chronological order containing automatically generated subtitles. This text can contain errors and some portions might not be relevant. Do your best at interpreting this as faithfully as possible.",
    }

    input_field_descriptions = '\n'.join([input_field_descriptions[field] for field in content])

    # Descriptions of output fields
    output_field_descriptions = {
        'statement_en': "* An exercise `statement`, in English, as it would appear in an exam about the lecture. Make sure the statement is clear, unambiguous and no guessing is required. Match the exercise to the user's `description`.",
        'statement_fr': "* A French translation of `statement_en`",
        'title_en': "* A `title` for the exercise, in English, limited to 10 words.",
        'title_fr': "* A French translation of `title_en`",
        'description_en': "* A `description` for the exercise, in English, using between 24 and 32 words, consisting of one sentence in the third person that conveys what the exercise is about, but not disclosing the solution.",
        'description_fr': "* A French translation of `description_en`",
        'solution_en': "* A clear, step-by-step `solution` for the exercise, in English. This should not just be hints on how to solve the exercise, but rather what would be given an A in an exam.",
        'solution_fr': "* A French translation of `solution_en`",
        'tags_en': "* A list of `tags` with the concepts, in English, the exercise is about. Make sure they are all distinct, in lowercase, not acronyms and sorted in descending order of relevance.",
    }

    if not include_solution:
        del output_field_descriptions['solution']

    output_field_descriptions = '\n'.join(output_field_descriptions.values())

    # Main content fields
    slides = 'slides' in content and content['slides']
    transcripts = 'transcripts' in content and content['transcripts']
    both = slides and transcripts

    if both:
        field_names = "`slides` and `transcripts`"
    elif slides:
        field_names = "`slides`"
    elif transcripts:
        field_names = "`transcripts`"
    else:
        field_names = ""

    system_prompt = f"""
Your task is to generate an exercise for an EPFL lecture based on the lecture material and a user request.

You will be given raw data of a video lecture, containing the following fields:
{input_field_descriptions}

In addition, the user will also provide an `description` with precise details about the exercise you should generate. 

Produce the following items:
{output_field_descriptions}

Make sure to comply with the following conditions:
* Do not copy exercises from the lecture content.
* Unless instructed otherwise, the exercise should remain in the context of the lecture and solved using the same methods.  
* Exercises must be well-defined, complete and solvable with the given information.
* Exercises can be as long as needed, but should not be longer than necessary.
* Output the exercise `statement` and `solution` as LaTeX code, not Markdown.
* From the lecture raw data, only use information about the actual content of the lecture.
* Do not include contact information, such as email addresses, phone numbers, or postal addresses.
"""

    return system_prompt


def build_human_prompt(content, description):
    human_prompt = f"""
Here is the lecture data:
{content}

And this is the user's `description` of the exercise:
> {description}
"""

    return human_prompt


if __name__ == '__main__':
    content = {'title': "A", 'description': "B", 'slides': ["aaa", "bbb"], 'transcripts': ["ccc", "ddd"]}
    system_prompt = build_system_prompt(content, include_solution=True)

    print(system_prompt)
