{{ opening }}

{% for hint in hints %}
<details>
<summary>{{ hint.title }}</summary>

{{ hint.body }}
</details>
{% endfor %}
{% if include_solution %}

<details>
<summary>{{ solution.title }}</summary>

{{ solution.body }}
</details>
{% endif %}
