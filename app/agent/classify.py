"""
This module contains a function to classify a conversation (list of messages) via an LLM
"""

from typing import Literal
from pydantic import BaseModel

from langchain_openai import ChatOpenAI

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)
from langchain.output_parsers import PydanticOutputParser

from app.config import config

################################################################
# Categories                                                   #
################################################################

pedagogical_sysprompts = {
    'base': """
# Pedagogical requirements
* Act as if you were a tutor or mentor for the user.
* If you are helping with an exercise or assignment, do not give the solution right away, but rather lay out directions or ask questions for the user to find the solution on their own.
* Your answer should help the user learn or understand.
* Do not use words or phrases that express doubt or provide a subjective opinion.
""",
    'socratic': """
# Pedagogical requirements
* Act as if you were a tutor or mentor, with a socratic, thought-provoking and question-based style, enhancing critical thinking and conceptual understanding.
* Use guided questioning to help students arrive at their own conclusions.
* Encourage deep reasoning by challenging assumptions and prompting reflection.
* Avoid simply giving answers; instead, promote self-discovery.
* Create productive struggle, thus supporting long-term retention.
* Build confidence by showing students they can figure things out independently.
* Adapt questions based on student responses to maintain the Zone of Proximal Development.
""",
    'creative': """
# Pedagogical requirements
* Act as if you were a tutor or mentor, with a creative, engaging, metaphor- and example-rich style, relating concepts to the real world or other subjects.
* Use analogies, metaphors, and storytelling to explain abstract concepts.
* Tap into students’ interests or background knowledge to create meaningful connections.
* Integrate visuals, diagrams, and interactive elements to support comprehension.
* Encourage students to generate their own examples, boosting active processing.
* Frequently check for understanding through casual conversations or low-stakes activities.
* Help learners transfer knowledge across contexts.
""",
    'iterative': """
# Pedagogical requirements
* Act as if you were a tutor or mentor, with a systematic, repair-focused and patient style, filling learning gaps and misconceptions.
* Start by diagnosing prior knowledge and misconceptions using careful questioning and diagnostic assessment.
* Re-teach foundational concepts with clear, structured explanations and scaffolded examples.
* Use spaced and interleaved practice to reinforce retention and promote flexible knowledge use.
* Break complex tasks into small, manageable chunks, supporting mastery at each stage.
* Frequently revisit and reinforce key ideas using retrieval practice.
* Balance correction with encouragement to prevent frustration, promoting a growth-oriented mindset.
""",
    'supportive': """
# Pedagogical requirements
* Act as if you were a tutor or mentor, with a supportive, emotionally attuned and confidence-building style, appeasing learning anxiety, boosting self-efficacy and granting students a safe space to grow.
* Build a strong rapport and safe learning environment, fostering trust and openness.
* Use positive reinforcement and strengths-based feedback to build confidence.
* Identify and work with emotional blocks to learning (e.g., anxiety, fear of failure).
* Encourage student voice and agency, validating feelings and input to boost intrinsic motivation.
* Gently scaffold challenges to match the student's readiness, nurturing a sense of competence and progress.
* Emphasize mindfulness, reflection, and encouragement, reducing cognitive overload and improving engagement.
""",
}


base_epfl_presidency_sysprompt = """
# Warning
Be careful with statements about people. Do not make any assumption that is not coming from the available information.
EPFL has one "President" and 6 "Vice Presidents", not to be confused with "Associate Vice Presidents".
"""

base_people_sysprompt = """
# Warning
Be careful with statements about people. Do not make any assumption that is not coming from the available information.
After using the `search_nodes` tool to find information about a person, use the `search_news` tool to find news articles about them.
"""

base_study_plan_sysprompt = """
# Warning
Currently there is no information available about the study plan in the system. However, here are the [study plans in French](https://www.epfl.ch/education/studies/reglement-et-procedure/plans_etudes/) and [in English](https://www.epfl.ch/education/studies/en/rules-and-procedures/study_plans/).
"""


course_categories = {
    'help-with-assignment': {
        'description': "Requests that present an exercise or question and want help with its solution.",
        'system_prompt': pedagogical_sysprompts,
    },
    'explain-concept': {
        'description': "Requests that ask a question about some specific concept or domain.",
        'system_prompt': pedagogical_sysprompts,
    },
    'other': {'description': "Other requests."},
}

categories = {
    'base': {
        'help-with-assignment': {
            'description': "Requests that present an exercise or question and want help with its solution.",
            'system_prompt': pedagogical_sysprompts,
            'tools': ['search_nodes'],
        },
        'explain-concept': {
            'description': "Requests that ask a question about some specific concept or domain.",
            'system_prompt': pedagogical_sysprompts,
            'tools': ['search_nodes'],
        },
        'epfl-presidency': {
            'description': "Explicit requests about the presidency of EPFL.",
            'system_prompt': base_epfl_presidency_sysprompt,
            'tools': ['get_orgchart', 'search_news'],
        },
        'epfl-vice-presidencies': {
            'description': "Explicit requests about the vice-presidencies of EPFL.",
            'system_prompt': base_epfl_presidency_sysprompt,
            'tools': ['get_orgchart', 'search_news'],
        },
        'people': {
            'description': "Requests about researchers or instructors at EPFL.",
            'system_prompt': base_people_sysprompt,
            'tools': ['get_orgchart', 'search_nodes'],
        },
        'lectures': {
            'description': "Requests about EPFL video lectures.",
            'tools': ['search_nodes'],
        },
        'exercises': {
            'description': "Requests that want to find exercises about some topic.",
            'tools': ['search_exercises'],
        },
        'courses': {
            'description': "Requests about EPFL courses.",
            'tools': ['search_nodes'],
        },
        'study-plan': {
            'description': "Requests about the EPFL study plan, for example about credits, pre-requisites or the availability of courses in a given plan.",
            'system_prompt': base_study_plan_sysprompt,
            'tools': ['search_nodes'],
        },
        'schedule': {
            'description': "Student requests about the time schedule of the classes.",
            'tools': ['search_nodes'],
        },
        'student-projects': {
            'description': "Explicit requests about student projects.",
            'tools': ['search_nodes'],
        },
        'internships': {
            'description': "Explicit requests about student internships.",
            'tools': ['search_nodes'],
        },
        'labs-or-units': {
            'description': "Requests about EPFL units (labs, centers, institutes, chairs, etc.).",
            'tools': ['search_nodes'],
        },
        'startups': {
            'description': "Explicit requests about EPFL startups or spin-off companies.",
            'tools': ['search_nodes'],
        },
        'news': {
            'description': "Explicit requests about news from EPFL.",
            'tools': ['search_news'],
        },
        'infrastructure': {
            'description': "Explicit requests about the infrastructure of EPFL, like rooms, buildings, toilets, showers, etc.",
            'tools': ['search_plan'],
        },
    },

    'lex': {
        'recruiting': {'description': "Requests about recruitment at EPFL, including PhD students, postdocs, researchers or any other EPFL staff member."},
        'contract-management': {'description': "Requests about the EPFL work contract for all kind of staff members."},
        'internal-processes': {'description': "Requests about internal processes at EPFL, like mandatory trainings or electing people for management positions."},
        'equipment': {'description': "Requests about equipment or material at EPFL, like purchasing some piece of equipment for research in a lab or regulations on office material."},
        'absences': {'description': "Requests about absences at EPFL, including paid leaves (holidays, medical leaves, maternity or paternity leaves, accidents, etc.) unpaid leaves, teleworking or other absences."},
        'epfl-presidency': {
            'description': "Explicit requests about the presidency of EPFL.",
            'system_prompt': base_epfl_presidency_sysprompt,
            'tools': ['get_orgchart', 'search_news'],
        },
        'epfl-vice-presidencies': {
            'description': "Explicit requests about the vice-presidencies of EPFL.",
            'system_prompt': base_epfl_presidency_sysprompt,
            'tools': ['get_orgchart', 'search_news'],
        },
    },
    'servicedesk': {
        'epfl': {'description': "Requests about EPFL."},
        'public': {'description': "Requests about Public."},
        'finances': {'description': "Requests about Finances."},
        'research': {'description': "Requests about Research."},
        'human-resources': {'description': "Requests about Human Resources."},
        'servicedesk': {'description': "Requests about Service Desk."},
    },
    'sac': {
        'guidelines': {'description': "Requests about guidelines and regulations."},
        'studies': {'description': "Requests about studies."},
        'other': {'description': "Other requests."},
    },
    'COURSE-X': course_categories,
}


def get_category_details(category_name, integration, style, style_prompt):
    if integration.startswith('COURSE-'):
        category_details = categories.get('COURSE-X', {}).get(category_name, {})
    else:
        category_details = categories.get(integration, {}).get(category_name, {})

    if 'system_prompt' in category_details and isinstance(category_details['system_prompt'], dict):
        system_prompts = category_details['system_prompt']
        category_details['system_prompt'] = system_prompts.get(style, system_prompts['base'])

    if style_prompt:
        style_prompt = style_prompt.strip()

    if style == 'custom' and style_prompt:
        category_details['system_prompt'] = f"""# Pedagogical requirements
{style_prompt}"""

    return category_details


################################################################

def classify_conversation(conversation, integration):
    # Select category integrations to send to the LLM
    if integration in categories:
        integration_categories = categories[integration]
    else:
        integration_categories = {}

    # Return if no categories for integration
    if not integration_categories:
        return None

    # Prepare system prompt
    categories_prompt = '\n'.join([f"* {category_name}: {integration_categories[category_name]['description']}" for category_name in integration_categories])
    system_prompt = f"""
You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on what the last request is about. 
The possible categories are the following:
{categories_prompt}
"""

    # Prepare human prompt (keep only human and ai messages in conversation)
    conversation = [m for m in conversation if isinstance(m, HumanMessage) or isinstance(m, AIMessage)]
    human_prompt = '\n\n'.join([f'{conversation_message.type}: {conversation_message.content}' for conversation_message in conversation])

    # Prepare response format
    class ConversationType(BaseModel, extra='allow'):
        model_config = {'json_schema_extra': {'additionalProperties': False}}

        category: Literal[*list(integration_categories.keys())]

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "conversation_type",
            "strict": True,
            "schema": ConversationType.model_json_schema()
        }
    }

    # Instantiate chat model and output parser
    model_name = 'gpt-4o-mini'
    model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=60)
    model = model.bind(response_format=response_format)
    parser = PydanticOutputParser(pydantic_object=ConversationType)

    # Gather the messages for the LLM input
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    # Send request to LLM
    try:
        output = model.invoke(input=messages)
    except Exception as e:
        print('[CLASSIFY]', "ERROR: LLM API call failed")
        print('[CLASSIFY]', e)
        return None

    # Parse output
    try:
        conversation_type = parser.parse(output.content)
    except Exception as e:
        print('[CLASSIFY]', "ERROR: Parsing LLM response failed")
        print('[CLASSIFY]', output.content)
        print('[CLASSIFY]', e)
        return None

    return conversation_type.category


if __name__ == '__main__':
    messages = [
        HumanMessage(content="A partir des données envoyées par l'engin spatial Voyager en 1979, l'ingénieur Linda Morabitoa découvert sur Io, un satellite de Jupiter, la première activité volcanique extraterrestre. Le panache de l'éruption s'élevait à 280 km d'altitude environ. Sachant que l'accélération due à la gravité à la surface de Io vaut 1.8 m·s^(−2), et supposant qu'elle demeure constante jusqu'à la hauteur maximale du panache, déterminez: 1. La vitesse à laquelle les débris étaient projetés? 2. Le temps qu'il leur fallait pour atteindre la hauteur maximale?"),
        AIMessage(content="Sorry, I don't know."),
        HumanMessage(content="Ah, I need holidays. Tell me how many holidays I am entitled to"),
    ]

    category = classify_conversation(messages, integration='lex')

    print(category)
