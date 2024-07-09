# EPFL Graph Chatbot

Chatbot for the EPFL Graph project 🤖

## Overview
The chatbot for the EPFL Graph is a service that leverages LLMs to provide answers in natural language about the data in the EPFL Graph as well as other EPFL-related services. It is deployed as an API using the [FastAPI](https://fastapi.tiangolo.com/) framework, and is implemented leveraging the [LangChain](https://python.langchain.com/v0.2/docs/introduction/) and [LangGraph](https://langchain-ai.github.io/langgraph/) Python packages.

Via the `/chat` endpoint, the user can engage in a conversation with an agent that will use the different tools at its disposal to provide answers to the user's requests. The following list covers the functions that are available for the agent to use:
* **search_nodes**: Searches for nodes in the EPFL Graph of one or more `node_type` matching a given `query` (e.g. "Course" about "solar cells") and returns a list of nodes with links that match the given query.
* **search_exercises**: Takes a `query` (e.g. "oscillators") and returns a list of exercises from the EXOSET database that best match the given query.
* **search_news**: Takes a `query` (e.g. "sustainability") and returns a list of official EPFL news that match the given query.

The chatbot is instructed to steer away from any discussion not appropriate or not concerning EPFL. However, since it uses LLMs, it can be affected by their [known issues](https://en.wikipedia.org/wiki/Large_language_model#Wider_impact), such as hallucinations, biases or other issues.

## Safety measures
A lot of effort has been put in making the chatbot less susceptible to hallucinations or biases when retrieving information from the tools. To that end, several measures have been put in place:
* The LLM is instructed to always provide a url linking to the relevant content on [GraphSearch](https://graphsearch.epfl.ch), [EXOSET](https://exoset.epfl.ch) or [EPFL news](https://actu.epfl.ch).
* Every time the LLM generates a message, the agent automatically checks whether it contains a link which was not returned by the tools, and rolls back and re-generates the message if that is the case.
* The `/chat` endpoint returns a list of `tool_interactions`, which is a history of the tool calls that the agent has performed. This information can be used to do further checks if needed and be displayed to the end user for transparency (e.g. "Searched for **Courses** related to **Nanotechnology**").  
* Should any sensitive information be supposed to be kept away from the LLM, the system is ready to put in place a way of obfuscating the actual content of the nodes in the EPFL Graph (e.g. by replacing people's names). This is not done by default as the information is considered to be of low risk, most of it being publicly available (publications, people's affiliations, courses, etc.).  

Despite all these efforts, the nature of LLMs makes it impossible to prevent undesired interactions completely. In addition, the EPFL Graph chatbot is at least as susceptible to adversarial attacks as its underlying LLM.

## Setup
Install this package in editable mode with
```
pip install -e .
```

Add a configuration file `config.ini` in the project root with the following content:
```
[database]
host: <host>
port: <port>
user: <user>
password: <pass>

[elasticsearch]
host: <host>
port: <port>
username: <user>
password: <pass>
cafile: </path/to/certificate/file>

[openai]
api_key: <openai_key>

[graphsearch]
base_url: <base url for node links>
```

Then deploy the API with
```
uvicorn main:app --reload --port 5100
```

Now the API should be listening on port `5100`. You can start interacting directly through HTTP requests or load the provided (temporary) frontend typing
```
localhost:5100
```
in a browser's URL bar.

## Docs
An OpenAPI documentation file is generated automatically by FastAPI. It can be accessed from the `/docs` endpoint.
