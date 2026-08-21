{% macro examples(example_set, framing) %}
### Examples

{% if framing %}
{{ framing }}

{% endif %}
{% for entry in example_set.examples %}
<example_{{ loop.index }}>
{{ example(entry) | trim }}
</example_{{ loop.index }}>
{% endfor %}
{% endmacro %}

{% macro example(entry) %}
{% for tag, text in entry.tags.items() %}
<{{ tag }}>
{{ text }}
</{{ tag }}>
{% endfor %}
{% endmacro %}
