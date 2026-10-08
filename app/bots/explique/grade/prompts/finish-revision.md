{% if lang_code == 'fr' %}
{% set heading, review = "À revoir :", "Réviser" %}
{% elif lang_code in ['de', 'gsw'] %}
{% set heading, review = "Nochmal anschauen:", "Wiederholen" %}
{% elif lang_code == 'it' %}
{% set heading, review = "Da rivedere:", "Ripassa" %}
{% else %}
{% set heading, review = "Worth revisiting:", "Revise" %}
{% endif %}
{# A point with nothing to say is left out; one with nothing to ask is listed without its link. #}
{% set points = revision.points | selectattr("next_step") | list %}
{% if points %}
**{{ heading }}**
{% for point in points %}
- {{ point.next_step }}{% if point.question %} [{{ review }} ↗](/?{{ {"models": review_model, "q": course_name ~ ": " ~ point.question} | urlencode }}){% endif +%}
{% endfor %}
{% endif %}
