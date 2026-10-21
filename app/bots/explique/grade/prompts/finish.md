{% if lang_code == 'fr' %}
{% set covered %}Tu as couvert **{{ topic.name }}**.{% endset %}
{% set quizzes_open %}Tes quiz d'entraînement sont maintenant ouverts :{% endset %}
{% set quiz_open %}Ton quiz d'entraînement est maintenant ouvert :{% endset %}
{% set quiz_on_moodle %}Ton quiz d'entraînement est maintenant ouvert ; tu le trouveras sur la page du cours dans Moodle.{% endset %}
{% set not_recorded %}Je n'ai pas pu enregistrer cela dans Moodle, ton quiz d'entraînement ne s'ouvrira donc pas. Merci d'en informer ton équipe enseignante ; elle peut te l'ouvrir.{% endset %}
{% set past_deadline %}La date limite de ton quiz d'entraînement sur ce sujet est passée, donc rien n'a été enregistré dans Moodle et le quiz reste fermé.{% endset %}
{% elif lang_code in ['de', 'gsw'] %}
{% set covered %}Du hast **{{ topic.name }}** abgedeckt.{% endset %}
{% set quizzes_open %}Deine Übungsquiz sind jetzt offen:{% endset %}
{% set quiz_open %}Dein Übungsquiz ist jetzt offen:{% endset %}
{% set quiz_on_moodle %}Dein Übungsquiz ist jetzt offen; du findest es auf der Kursseite in Moodle.{% endset %}
{% set not_recorded %}Ich konnte das nicht in Moodle erfassen, daher öffnet sich dein Übungsquiz nicht. Bitte informiere dein Lehrteam; es kann es für dich öffnen.{% endset %}
{% set past_deadline %}Die Frist für dein Übungsquiz zu diesem Thema ist abgelaufen, daher wurde nichts in Moodle erfasst und das Quiz bleibt geschlossen.{% endset %}
{% elif lang_code == 'it' %}
{% set covered %}Hai coperto **{{ topic.name }}**.{% endset %}
{% set quizzes_open %}I tuoi quiz di esercitazione sono ora aperti:{% endset %}
{% set quiz_open %}Il tuo quiz di esercitazione è ora aperto:{% endset %}
{% set quiz_on_moodle %}Il tuo quiz di esercitazione è ora aperto; lo trovi sulla pagina del corso in Moodle.{% endset %}
{% set not_recorded %}Non sono riuscito a registrarlo su Moodle, quindi il tuo quiz di esercitazione non si aprirà. Segnalalo al tuo team docente; possono aprirtelo loro.{% endset %}
{% set past_deadline %}La scadenza del tuo quiz di esercitazione su questo argomento è passata, quindi non è stato registrato nulla su Moodle e il quiz resta chiuso.{% endset %}
{% else %}
{% set covered %}You've covered **{{ topic.name }}**.{% endset %}
{% set quizzes_open %}Your practice quizzes are now open:{% endset %}
{% set quiz_open %}Your practice quiz is now open:{% endset %}
{% set quiz_on_moodle %}Your practice quiz is now open; you'll find it on the course page in Moodle.{% endset %}
{% set not_recorded %}I couldn't record this in Moodle, so your practice quiz won't open. Please inform your teaching team; they can open it for you.{% endset %}
{% set past_deadline %}The deadline for your practice quiz on this topic has passed, so nothing was recorded in Moodle and the quiz stays closed.{% endset %}
{% endif %}
{{ covered }} {{ finish_marker }}
{% if access.assessment_urls | length > 1 %}
{{ quizzes_open }}
{% for url in access.assessment_urls %}
- {{ url }}
{% endfor %}
{% elif access.assessment_urls %}
{{ quiz_open }} {{ access.assessment_urls[0] }}
{% elif access.recorded %}
{{ quiz_on_moodle }}
{% elif access.failed %}
{{ not_recorded }}
{% elif access.outcome == "past_deadline" %}
{{ past_deadline }}
{% endif %}
