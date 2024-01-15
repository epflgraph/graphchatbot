# EPFL Graph Chatbot

Chatbot for the EPFL Graph project 🤖

## Overview
The chatbot for the EPFL Graph is a service that leverages LLMs to provide answers in natural language about the data in the EPFL Graph as well as other EPFL-related services. It is deployed as an API using the [FastAPI](https://fastapi.tiangolo.com/) framework.

Through the `/chat` endpoint, the user can engage in a conversation with an agent that will use the different tools at its disposal to provide answers to the user's requests. The following list covers the functions that are available for the agent to use:
* **Ask EPFL Graph**: Takes a request about the EPFL Graph in natural language (e.g. "courses related to solar cells") and returns a nodeset that roughly gives answer to it.
* **Search EXOSET exercises**: Takes a concept in natural language (e.g. "oscillators") and returns a list of exercises from the EXOSET database that (likely) match the given concept.
* **Search EPFL news**: Takes a small query in natural language (e.g. "sustainability") and returns a list of official EPFL news that match the given query.

The chatbot is instructed to steer away from any discussion not appropriate or not concerning EPFL. However, since it uses LLMs, it can be affected by their [known issues](https://en.wikipedia.org/wiki/Large_language_model#Wider_impact), such as hallucinations, biases or other issues.

## EPFL Graph tool
A lot of effort has been put in making the chatbot less susceptible to hallucinations or biases when retrieving information from the EPFL Graph. To that end, the actual content of the graph has been protected from the LLM, and hence approaches like RAG have been discarded. Instead, we leverage the known structure of the graph to generate a complex query with the LLM that is later checked and followed away from it, and only a list of obfuscated results are returned to the agent.

### Outline
Here is a simplified outline of how it works, together with an example:
1. The user sends a request to the endpoint `/chat`, who calls the agent (e.g. "Hey I would like to know who is teaching the course CS-411").
2. The agent decides to use the EPFL Graph tool (e.g. with input "teachers of the course CS-411").
3. The EPFL Graph tool receives the input and uses an LLM to generate a list of instructions to be followed on the graph to answer the request, e.g.
   ```
   A = Search(Course, CS-411)
   B = Neighborhood(A, Person)
   Return(B, Person)
   ```
4. The tool then validates thoroughly these instructions and, in case there are no issues, executes them on the graph to retrieve a nodeset, e.g.
   ```
   [
     {'NodeKey': 111111, 'NodeType': 'Person', 'Title': 'Patrick Jermann'},
     {'NodeKey': 222222, 'NodeType': 'Person', 'Title': 'Pierre Dillenbourg'}
   ]
   ```
5. The tool now does two things. It first stores this nodeset as is somewhere accessible from the function that calls the agent. Second, it obfuscates the nodeset however needed and returns it to the agent. This typically involves keeping only the first 10 nodes, but can also mean replacing people's names with placeholders, e.g.
   ```
   [
     {'NodeKey': 111111, 'NodeType': 'Person', 'Title': 'John Doe'},
     {'NodeKey': 222222, 'NodeType': 'Person', 'Title': 'Richard Roe'}
   ]
   ```
6. The agent receives the obfuscated nodeset and prepares an answer based on it (e.g. "The teachers of the course CS-411 are John Doe and Richard Roe.").
7. The function who called the agent, and has access to the unobfuscated nodeset, restores the names into the answer message (e.g. "The teachers of the course CS-411 are Patrick Jermann and Pierre Dillenbourg").
8. The endpoint returns the user a response including this message and other context information, like an explanation of the path that was followed in the graph to reach the nodeset ("Showing **People** related to the **Course** *Digital Education*").

### Benefits
This strategy offers some benefits over other approaches that would expose the content of the graph to the LLM:
* No need to set up a RAG system to retrieve the most likely nodes for the LLM to see.
* Fewer tokens are exchanged, which leads to less latency, cost and energy usage.
* Data privacy. The only information sent to the LLM is the user input, nothing else.
* Results can be cached, since we assume the same query will always give rise to the same set of instructions,
regardless of whether the data has changed.
* Certain very complicated or sensitive queries can be artificially cached if needed, again regardless of whether the data has changed.
* Sometimes we can recover from a wrong set of instructions and ask again thanks to the strict syntax.
* Protection against hallucinations, to some extent. If the LLM hallucinates, two things can happen:
  * The instructions are invalid (e.g. use an operator that does not exist). In this case we return no nodes.
  * The instructions produce a wrong nodeset (e.g. people related to the Concept "Digital Education" instead of the Course "Digital Education"). Even in this case, we can explain how it was constructed, and we know the data comes from the graph. The response is not *false*, but rather answers a different question.

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
cafile: /path/to/certificate/file

[openai]
api_key: <openai_key>
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
