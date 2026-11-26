{% include "invite.md" +%}
{% if lang_code == 'fr' %}
Attention : la date limite de ton quiz d'entraînement sur ce sujet est passée, donc rien de ce que tu fais ici ne sera enregistré dans Moodle et le quiz ne s'ouvrira pas à la fin. Tu peux quand même continuer : l'exercice fonctionne, mais il ne comptera pas.
{% elif lang_code in ['de', 'gsw'] %}
Ein Hinweis: Die Frist für dein Übungsquiz zu diesem Thema ist abgelaufen. Deshalb wird nichts, was du hier machst, in Moodle erfasst, und das Quiz öffnet sich am Ende nicht. Du kannst trotzdem weitermachen: Die Übung funktioniert, sie zählt nur nicht.
{% elif lang_code == 'it' %}
Attenzione: la scadenza del tuo quiz di esercitazione su questo argomento è passata, quindi quello che fai qui non verrà registrato su Moodle e il quiz non si aprirà alla fine. Puoi comunque continuare: l'esercizio funziona, ma non conterà.
{% else %}
One catch: the deadline for your practice quiz on this topic has passed, so whatever you cover here won't be recorded in Moodle and the quiz won't open at the end. You're welcome to carry on anyway; the exercise still works, it just won't count.
{% endif %}
