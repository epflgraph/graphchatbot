from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.agents.loading import AGENT_TO_CLASS
from langchain.schema import AgentAction, AgentFinish

from app.tools.graph import graph_answers


class CustomOpenAIFunctionsAgent(OpenAIFunctionsAgent):
    """
    Custom agent inheriting from langchain's OpenAIFunctionsAgent.
    It keeps the same functionality but also stores the results of the function calls.
    """
    results = []

    def plan(
        self,
        intermediate_steps,
        *args,
        **kwargs,
    ):
        if intermediate_steps:
            agent_action, result = intermediate_steps[-1]   # can't use this result as it's obfuscated

            # Store results from last function call
            if agent_action.tool == 'Ask_EPFL_Graph':
                human_input = agent_action.tool_input['human_input']
                if human_input in graph_answers:
                    result = graph_answers[human_input]

                self.results.append(result)
        else:
            # First interaction, clear results_list
            self.results = []

        print("[AGENT]", "Planning what to do next")

        # Call super function to actually plan
        agent_decision = super().plan(intermediate_steps, *args, **kwargs)

        if isinstance(agent_decision, AgentAction):
            print("[AGENT]", f"Chose to use tool `{agent_decision.tool}` with input `{agent_decision.tool_input}`")
        elif isinstance(agent_decision, AgentFinish):
            print("[AGENT]", "Chose to finish execution")
        else:
            # Unreachable
            raise ValueError(f"Agent planned a {agent_decision}, only AgentAction or AgentFinish are supported.")

        return agent_decision


# Register agent type in langchain's catalog
CUSTOM_OPENAI_FUNCTIONS = "custom-openai-functions"
AGENT_TO_CLASS[CUSTOM_OPENAI_FUNCTIONS] = CustomOpenAIFunctionsAgent
