{% if lang_code == 'fr' %}
Cette session est terminée{% if topic %}. Tu as déjà couvert **{{ topic.name }}**{% endif %}. Pour un autre sujet, démarre une nouvelle discussion.
{% elif lang_code in ['de', 'gsw'] %}
Diese Sitzung ist beendet{% if topic %}. Du hast **{{ topic.name }}** bereits abgedeckt{% endif %}. Für ein anderes Thema starte einen neuen Chat.
{% elif lang_code == 'it' %}
Questa sessione è conclusa{% if topic %}. Hai già coperto **{{ topic.name }}**{% endif %}. Per un altro argomento, avvia una nuova chat.
{% else %}
This session is over{% if topic %}. You've already covered **{{ topic.name }}**{% endif %}. To work on another topic, start a new chat.
{% endif %}
