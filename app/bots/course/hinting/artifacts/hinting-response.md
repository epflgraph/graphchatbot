{% for section in sections %}
{% if section.type == "text" %}
{{ section.content }}

{% else %}
<details>
<summary>{{ section.title }}</summary>

{{ section.content }}
</details>
{% endif %}
{% endfor %}
