"""
This module defines a child class of langchain's standard Agent class, to be used as the chatbot's wrapper agent class.

This is not strictly needed, and one could instantiate the wrapper agents directly using the langchain's standard Agent class.
However, in that case the agent's tools would not be able to return anything directly to the caller function, and could only do so through the
LLM (and subject to changes under the LLM's criterion).

Instantiating the wrapper agent with this custom child class allows to pass a variable results as an attribute from the tool to the caller function,
even transparently for the LLM. This is useful in many ways, like for example
* Reducing the tokens used by the LLM (decreasing cost, latency and used energy).
For example, we can remove the node descriptions for the LLM but return them to the frontend in case we want to display them.
This can also improve the LLM's performance, as we can simplify the tool's output for the LLM, which likely makes the LLM's output better
or at least more predictable, all while still keeping the full information for later.
* Obfuscating information to the LLM. For instance, if the tool returns the node corresponding to Patrick Jermann,
we could replace this name by John Doe, send it to the LLM and then replacing the correct name back again before returning to the frontend,
thus protecting the person's anonymity.
"""

from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.agents.loading import AGENT_TO_CLASS
from langchain.schema import AgentAction, AgentFinish

from app.deprecated.tools.graph import graph_answers


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
