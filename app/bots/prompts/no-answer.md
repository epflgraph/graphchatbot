{% if lang_code == 'fr' %}
Désolé, une erreur s'est produite lors de la génération de cette réponse. Réessaie.
{% elif lang_code in ['de', 'gsw'] %}
Entschuldigung, bei der Erstellung dieser Antwort ist ein Fehler aufgetreten. Bitte versuch es noch einmal.
{% elif lang_code == 'it' %}
Spiacenti, si è verificato un problema durante la generazione di questa risposta. Riprova.
{% else %}
Sorry, an issue occurred while generating this response. Please try again.
{% endif %}
