{% if lang_code == 'fr' %}
J'ai besoin d'un sujet avant de commencer. Choisis-en un parmi ceux-ci :

{% include 'topic-list.md' %}

Réponds avec le nom du sujet exactement tel qu'il est écrit, ou son numéro seul, comme `{{ topics|length }}`.
{% elif lang_code in ['de', 'gsw'] %}
Ich brauche ein Thema, bevor wir beginnen können. Wähl eines davon:

{% include 'topic-list.md' %}

Antworte mit dem Namen des Themas genau so, wie er geschrieben steht, oder mit seiner Nummer allein, etwa `{{ topics|length }}`.
{% elif lang_code == 'it' %}
Mi serve un argomento prima di iniziare. Scegline uno tra questi:

{% include 'topic-list.md' %}

Rispondi con il nome dell'argomento esattamente come è scritto, oppure con il suo numero da solo, come `{{ topics|length }}`.
{% else %}
I need a topic before we can start. Choose one of these:

{% include 'topic-list.md' %}

Answer with the topic's name exactly as written, or its number on its own, like `{{ topics|length }}`.
{% endif %}
