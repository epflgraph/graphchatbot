from pydantic import BaseModel

from langchain_openai import ChatOpenAI

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)
from langchain.output_parsers import PydanticOutputParser

from app.config import config

from app.agent.tools.nodes import search_nodes

################################################################
# LLM expert                                                   #
################################################################


class ExpertResponse(BaseModel, extra='allow'):
    model_config = {'json_schema_extra': {"additionalProperties": False}}

    answer: str
    tags: list[str]


response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "expert_response",
        "strict": True,
        "schema": ExpertResponse.model_json_schema()
    }
}

# Instantiate chat model
model_name = 'gpt-4o-mini'
model = ChatOpenAI(model=model_name, temperature=0, openai_api_key=config['openai']['api_key'], request_timeout=30).bind(response_format=response_format)
parser = PydanticOutputParser(pydantic_object=ExpertResponse)


def call_llm(request, domain):
    # Prepare system prompt of expert
    system_prompt = f"""
    You are an academic expert in the domain of {domain}.
    You will receive a request from the user, typically a student, related to your field of expertise.

    Your task is to respond to that request as if you were a teacher or mentor for the user in the following way:
    * If the request is very simple, and could be answered for instance by looking something up on Wikipedia, do provide a direct response.
    * For more complex requests, like computations, university assignments, or more detailed explanations, do not give away the solution but rather lay out directions for the user to find the solution on their own.

    In your response, in addition to the `answer` also provide a short list of very specific `tags`, containing the fundamental concepts that best represent your answer.

    General considerations:
    * Your `answer` should help the user learn or understand.
    * Remember your role is that of a teacher or mentor, but do not mention what your role is.
    * Always give your `answer` in the same language as the request.
    * Make sure your answer is correct, precise and clear, and addresses the request from the user.
    * Do not use words or phrases that express doubt or provide a subjective opinion. Remember you are an expert in {domain}.
    * Provide the list of `tags` in English, and give at most 3 of them.
    """

    # Gather the messages for the LLM input
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=request),
    ]

    # Send request to LLM
    try:
        output = model.invoke(input=messages)
    except Exception as e:
        print('[EXPERT TOOL]', "ERROR: LLM API call failed")
        print('[EXPERT TOOL]', e)
        return {'answer': "", 'tags': []}

    # Parse output
    try:
        response = parser.parse(output.content)
    except Exception as e:
        print('[EXPERT TOOL]', "ERROR: Parsing LLM response failed")
        print('[EXPERT TOOL]', output.content)
        print('[EXPERT TOOL]', e)
        return {'answer': "", 'tags': []}

    return {
        'answer': response.answer,
        'tags': response.tags,
    }


################################################################
# Tool function                                                #
################################################################

def ask_expert(request: str, domain: str) -> dict:
    """
    Make a request in natural language to an academic expert of any knowledge domain, and return their answer in natural language as well as a list of nodes of the knowledge graph of EPFL.
    """

    print('[EXPERT TOOL]', f"Called `ask_expert` tool with request=`{request[:100]}` and domain=`{domain}`")

    # Call expert LLM to get an answer and a list of tags
    response = call_llm(request, domain)

    print('[EXPERT TOOL]', f"Got answer `{response['answer'][:100]}` and tags `{response['tags']}` from LLM expert")

    # Use the search_nodes tool to fetch nodes matching the LLM-generated tags
    nodes = []
    for tag in response['tags'][:5]:
        tag_nodes = search_nodes(query=tag, node_type='Concept')
        nodes += tag_nodes

    # Remove possible duplicate nodes
    nodes = list({(node['type'], node['id']): node for node in nodes}.values())

    print('[EXPERT TOOL]', f"Got {[(node['type'], node['id']) for node in nodes]} nodes for the returned tags.")

    return {'answer': response['answer'], 'nodes': nodes}


if __name__ == '__main__':
    response = ask_expert("Explain what is Hausdorff dimension", domain="fractal geometry")
    print(response)
