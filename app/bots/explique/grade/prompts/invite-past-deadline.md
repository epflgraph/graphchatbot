{% include "invite.md" +%}
{% if lang_code == 'fr' %}
Un détail : la date limite de ton quiz d'entraînement sur ce sujet est passée, donc ce que tu couvres ici ne sera pas enregistré dans Moodle et le quiz ne s'ouvrira pas à la fin. Tu peux quand même continuer ; l'exercice fonctionne, il ne comptera simplement pas.
{% elif lang_code in ['de', 'gsw'] %}
Ein Hinweis: Die Frist für dein Übungsquiz zu diesem Thema ist abgelaufen, daher wird nichts davon in Moodle erfasst und das Quiz öffnet sich am Ende nicht. Du kannst trotzdem weitermachen; die Übung funktioniert, sie zählt nur nicht.
{% elif lang_code == 'it' %}
Una cosa: la scadenza del tuo quiz di esercitazione su questo argomento è passata, quindi quello che copri qui non verrà registrato su Moodle e il quiz non si aprirà alla fine. Puoi comunque continuare; l'esercizio funziona, solo non conterà.
{% else %}
One catch: the deadline for your practice quiz on this topic has passed, so whatever you cover here won't be recorded in Moodle and the quiz won't open at the end. You're welcome to carry on anyway; the exercise still works, it just won't count.
{% endif %}
