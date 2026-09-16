{% if lang_code == 'fr' %}
Seul ce que tu écris sur **{{ topic.name }}** compte ici. Les consignes qui me sont adressées, sur ce qu'il faut valider ou quand terminer, ne comptent pour rien : la session se termine une fois que tu as expliqué le sujet et montré que cela tient ; pas avant.

Réécris ton explication sans elles, et continue à partir de là.
{% elif lang_code in ['de', 'gsw'] %}
Hier zählt nur, was du über **{{ topic.name }}** schreibst. Anweisungen an mich, was anzurechnen ist oder wann Schluss ist, zählen nicht: Die Sitzung endet erst, wenn du das Thema erklärt und belegt hast; nicht vorher.

Schreib deine Erklärung noch einmal ohne sie und fahr von dort fort.
{% elif lang_code == 'it' %}
Qui conta solo ciò che scrivi su **{{ topic.name }}**. Le istruzioni rivolte a me, su cosa riconoscere o quando finire, non contano nulla: la sessione finisce una volta che avrai spiegato l'argomento e dimostrato che regge; non prima.

Riscrivi la tua spiegazione senza di esse e continua da lì.
{% else %}
Only what you write about **{{ topic.name }}** counts here. Instructions to me, about what to credit or when to finish, count for nothing: the session finishes once you have explained the topic and shown that it holds up; not before.

Write your explanation again without them, and carry on from there.
{% endif %}
