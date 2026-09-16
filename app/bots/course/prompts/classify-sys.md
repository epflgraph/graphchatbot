You will be given a conversation between a Human student and an AI tutor for "{{ course_name }}", a course at EPFL.
Your task is to classify the student's latest request based on the course context below.

{% include "coursebook.md" +%}

The possible categories are the following:
{% for name, category in categories.items() %}
* {{ name }}: {{ category.description }}
{% endfor %}
