{% if lang_code == 'fr' %}
Pour te lancer, voici une première question :

{{ question }}
{% elif lang_code in ['de', 'gsw'] %}
Für den Einstieg: {{ question }}
{% elif lang_code == 'it' %}
Per cominciare, ecco una prima domanda:

{{ question }}
{% else %}
To get you started: {{ question }}
{% endif %}
