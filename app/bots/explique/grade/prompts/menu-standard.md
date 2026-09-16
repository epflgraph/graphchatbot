{% if lang_code == 'fr' %}
Quand tu veux. Choisis le sujet sur lequel tu souhaites être évalué :

{% include 'topic-list.md' %}

Réponds avec le nom du sujet exactement tel qu'il est écrit, ou son numéro seul, comme `{{ topics|length }}`.
{% elif lang_code in ['de', 'gsw'] %}
Bereit, wenn du es bist. Wähl das Thema, in dem du geprüft werden möchtest:

{% include 'topic-list.md' %}

Antworte mit dem Namen des Themas genau so, wie er geschrieben steht, oder mit seiner Nummer allein, etwa `{{ topics|length }}`.
{% elif lang_code == 'it' %}
Quando vuoi. Scegli l'argomento su cui vuoi essere valutato:

{% include 'topic-list.md' %}

Rispondi con il nome dell'argomento esattamente come è scritto, oppure con il suo numero da solo, come `{{ topics|length }}`.
{% else %}
Ready when you are. Pick the topic you would like to be graded on:

{% include 'topic-list.md' %}

Answer with the topic's name exactly as written, or its number on its own, like `{{ topics|length }}`.
{% if not lang_code %}You can write in English, French, German or Italian.{% endif %}
{% endif %}
