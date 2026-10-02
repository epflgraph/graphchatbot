{% for topic in topics %}
{{ loop.index }}. **{{ topic.name }}**
{% endfor %}
