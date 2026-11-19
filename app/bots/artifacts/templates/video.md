{% if player -%}
<video>
{{ player }}
</video>
{%- if timestamp %}

[▶️ MediaSpace · {{ timestamp }}]({{ link }})
{%- endif %}
{%- else -%}
<{{ link }}>
{%- endif %}
