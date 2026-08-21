You will be given a conversation between a Human and an AI system.
Your task is to classify the conversation based on the last request.
The possible categories are the following:
{% for name, category in categories.items() %}
* {{ name }}: {{ category.description }}
{% endfor %}
