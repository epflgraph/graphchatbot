{% if lang_code == 'fr' %}
Sujet : **{{ topic.name }}**.

C'est ta preuve de travail : ton quiz d'entraînement ne s'ouvre qu'une fois ce sujet expliqué et vérifié.

Explique-le avec tes propres mots, comme si tu l'enseignais à quelqu'un qui le découvre. Prends toute la place qu'il te faut.
{% elif lang_code in ['de', 'gsw'] %}
Thema: **{{ topic.name }}**.

Das ist dein Arbeitsnachweis: dein Übungsquiz öffnet sich erst, wenn du dieses Thema erklärt und belegt hast.

Erklär es in eigenen Worten, als würdest du es jemandem beibringen, der es zum ersten Mal sieht. Nimm dir so viel Raum, wie du brauchst.
{% elif lang_code == 'it' %}
Argomento: **{{ topic.name }}**.

Questa è la tua prova di lavoro: il quiz di esercitazione si apre solo dopo che avrai spiegato questo argomento e dimostrato che regge.

Spiegalo con parole tue, come se lo insegnassi a qualcuno che lo vede per la prima volta. Prenditi tutto lo spazio che ti serve.
{% else %}
Topic: **{{ topic.name }}**.

This is your proof of work: your practice quiz opens only once you have explained this topic and shown that it holds up.

Explain it in your own words, as though you were teaching it to someone seeing it for the first time. Take as much space as you need.
{% endif %}
