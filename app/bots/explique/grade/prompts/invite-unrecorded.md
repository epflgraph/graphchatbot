{% include "invite.md" +%}
{% if lang_code == 'fr' %}
Attention : je ne te trouve pas parmi les inscrits de ce cours sur Moodle, donc rien de ce que tu fais ici ne sera enregistré et ton quiz d'entraînement ne s'ouvrira pas à la fin. Merci de le signaler à ton équipe enseignante. En attendant, tu peux continuer : l'exercice fonctionne, mais il ne comptera pas.
{% elif lang_code in ['de', 'gsw'] %}
Ein Hinweis: Ich finde dich auf Moodle nicht unter den Teilnehmenden dieses Kurses. Deshalb wird nichts, was du hier machst, erfasst, und dein Übungsquiz öffnet sich am Ende nicht. Bitte melde das deinem Lehrteam. Du kannst in der Zwischenzeit trotzdem weitermachen: Die Übung funktioniert, sie zählt nur nicht.
{% elif lang_code == 'it' %}
Attenzione: non ti trovo tra gli iscritti a questo corso su Moodle, quindi quello che fai qui non verrà registrato e il tuo quiz di esercitazione non si aprirà alla fine. Per favore, segnalalo ai tuoi docenti. Nel frattempo puoi continuare: l'esercizio funziona, ma non conterà.
{% else %}
One catch: I can't find you on this course in Moodle, so whatever you cover here won't be recorded and your practice quiz won't open at the end. Please tell your teaching team. You're welcome to carry on in the meantime; the exercise still works, it just won't count.
{% endif %}
