{% if lang_code == 'fr' %}
Cet exercice est terminé et ne peut pas être rouvert.
{% elif lang_code in ['de', 'gsw'] %}
Diese Übung ist abgeschlossen und kann nicht wieder geöffnet werden.
{% elif lang_code == 'it' %}
Questo esercizio è concluso e non può essere riaperto.
{% else %}
This exercise is finished and cannot be reopened.
{% endif %}
