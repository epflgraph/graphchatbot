{% if lang_code == 'fr' %}
Sujet : **{{ topic.name }}**.

Une erreur s'est produite lors de la préparation du plan de cette session. Réessaie plus tard.
{% elif lang_code in ['de', 'gsw'] %}
Thema: **{{ topic.name }}**.

Beim Erstellen des Plans für diese Sitzung ist ein Fehler aufgetreten. Versuch es später noch einmal.
{% elif lang_code == 'it' %}
Argomento: **{{ topic.name }}**.

Si è verificato un errore durante la preparazione del piano di questa sessione. Riprova più tardi.
{% else %}
Topic: **{{ topic.name }}**.

An error occurred while preparing the plan for this session. Please try again later.
{% endif %}
