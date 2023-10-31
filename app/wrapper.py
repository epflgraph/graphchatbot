from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from langchain.prompts.chat import MessagesPlaceholder
from langchain.agents import Tool, AgentType, initialize_agent

from app.config import config
from app.prompts import system_messages


def get_hobby(name):
    if name == "Thomas":
        return "Surfing"
    elif name == "Jerry":
        return "Knitting"

    return "Traveling"


def create_chain(memory_key):
    chat = ChatOpenAI(temperature=0, openai_api_key=config['openai']['api_key'])

    tools = [Tool(name='Hobby', func=get_hobby, description="useful to know someone's hobby")]

    memory = ConversationBufferMemory(memory_key=memory_key, return_messages=True)

    agent_kwargs = {
        'system_message': SystemMessage(content=system_messages['pirate']),         # system prompt of the agent
        'extra_prompt_messages': [MessagesPlaceholder(variable_name=memory_key)]    # placeholder for history messages
    }

    return initialize_agent(
        tools=tools,
        llm=chat,
        agent=AgentType.OPENAI_FUNCTIONS,
        memory=memory,
        agent_kwargs=agent_kwargs,
        verbose=True,
        max_execution_time=5
    )


def get_chain(memory_key):
    # Create new chain if it does not exist already
    if memory_key not in chains:
        chains[memory_key] = create_chain(memory_key)

    return chains[memory_key]


# Initialise object to store chains
chains = {}

################################################################


def chat(conversation_id, human_input):
    chain = get_chain(conversation_id)

    output = chain.run(human_input)

    return {'message': output}
