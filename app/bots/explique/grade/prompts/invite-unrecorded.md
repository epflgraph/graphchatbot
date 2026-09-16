{% include "invite.md" +%}
{% if lang_code == 'fr' %}
Un détail : je ne te trouve pas dans ce cours sur Moodle, donc ce que tu couvres ici ne sera pas enregistré et ton quiz d'entraînement ne s'ouvrira pas à la fin. Merci de le signaler à ton équipe enseignante. Tu peux continuer en attendant ; l'exercice fonctionne, il ne comptera simplement pas.
{% elif lang_code in ['de', 'gsw'] %}
Ein Hinweis: Ich finde dich in diesem Kurs nicht auf Moodle, daher wird nichts davon erfasst und dein Übungsquiz öffnet sich am Ende nicht. Bitte melde das deinem Lehrteam. Du kannst in der Zwischenzeit weitermachen; die Übung funktioniert, sie zählt nur nicht.
{% elif lang_code == 'it' %}
Una cosa: non ti trovo in questo corso su Moodle, quindi quello che copri qui non verrà registrato e il tuo quiz di esercitazione non si aprirà alla fine. Segnalalo al tuo team docente. Nel frattempo puoi continuare; l'esercizio funziona, solo non conterà.
{% else %}
One catch: I can't find you on this course in Moodle, so whatever you cover here won't be recorded and your practice quiz won't open at the end. Please tell your teaching team. You're welcome to carry on in the meantime; the exercise still works, it just won't count.
{% endif %}
