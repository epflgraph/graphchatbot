{% if lang_code == 'fr' %}
Sujet : **{{ topic.name }}**.

C'est ici que tu montres que tu as travaillé ce sujet : ton quiz d'entraînement ne s'ouvre qu'une fois que tu l'as expliqué et que ton explication tient la route.

Explique-le avec tes propres mots, comme si tu l'enseignais à quelqu'un qui le découvre. Tu peux développer autant que tu veux.
{% elif lang_code in ['de', 'gsw'] %}
Thema: **{{ topic.name }}**.

Hier zeigst du, dass du dieses Thema erarbeitet hast: Dein Übungsquiz öffnet sich erst, wenn du es erklärt hast und deine Erklärung standhält.

Erklär es mit eigenen Worten, als würdest du es jemandem beibringen, der zum ersten Mal davon hört. Du kannst so ausführlich sein, wie du möchtest.
{% elif lang_code == 'it' %}
Argomento: **{{ topic.name }}**.

Qui dimostri di aver studiato questo argomento: il quiz di esercitazione si apre solo dopo che l'avrai spiegato e avrai mostrato che la tua spiegazione regge.

Spiegalo con parole tue, come se lo insegnassi a qualcuno che lo vede per la prima volta. Prenditi tutto lo spazio che ti serve.
{% else %}
Topic: **{{ topic.name }}**.

This is your proof of work: your practice quiz opens only once you have explained this topic and shown that it holds up.

Explain it in your own words, as though you were teaching it to someone seeing it for the first time. Take as much space as you need.
{% endif %}
