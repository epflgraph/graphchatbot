from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)


def build_prompt_from_message_list(messages):
    # Prepare human prompt
    human_prompt = []
    for message in messages:
        # Keep only human and ai messages
        if message.type not in ('human', 'ai'):
            continue

        # Extract only text from messages to send (otherwise images or other media types can fill the context window)
        if isinstance(message.content, str):
            message_content = message.content
        else:
            message_content = '\n'.join([content_piece['text'] for content_piece in message.content if content_piece['type'] == 'text'])

        human_prompt.append(f'----{message.type.upper()}----\n{message_content}')
    human_prompt = '\n\n'.join(human_prompt)

    return human_prompt


async def generate_structured_response(model, system_prompt, human_prompt, pydantic_base_model):
    # Gather the messages for the LLM input
    input_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    # Instantiate chat model
    model = model.with_structured_output(pydantic_base_model)

    # Send request to LLM
    try:
        result = await model.ainvoke(input=input_messages)
    except Exception as e:
        print('[PREMODEL]', "ERROR: Feedback call failed")
        print('[PREMODEL]', e)
        return

    return result
