{% if lang_code == 'fr' %}
La session ne commence qu'une fois que tu as choisi l'un de ces sujets :

{% include 'topic-list.md' %}

Réponds avec le nom du sujet exactement tel qu'il est écrit, ou son numéro seul, comme `{{ topics|length }}`. Rien d'autre n'ouvre la session.

Si aucun de ces sujets ne correspond à ce que tu attendais, ou si tu ne sais pas quoi faire ici, adresse-toi à ton équipe enseignante.
{% elif lang_code in ['de', 'gsw'] %}
Die Sitzung beginnt erst, wenn du eines dieser Themen wählst:

{% include 'topic-list.md' %}

Antworte mit dem Namen des Themas genau so, wie er geschrieben steht, oder mit seiner Nummer allein, etwa `{{ topics|length }}`. Nichts anderes öffnet die Sitzung.

Wenn keines davon dem entspricht, was du erwartet hast, oder du nicht sicher bist, was hier zu tun ist, wende dich an dein Lehrteam.
{% elif lang_code == 'it' %}
La sessione inizia solo dopo che avrai scelto uno di questi argomenti:

{% include 'topic-list.md' %}

Rispondi con il nome dell'argomento esattamente come è scritto, oppure con il suo numero da solo, come `{{ topics|length }}`. Nient'altro apre la sessione.

Se nessuno di questi è quello che ti aspettavi, o non sai bene cosa fare qui, rivolgiti al tuo team docente.
{% else %}
The session only starts once you choose one of these:

{% include 'topic-list.md' %}

Answer with the topic's name exactly as written, or its number on its own, like `{{ topics|length }}`. Nothing else opens the session.

If none of these is what you expected, or you are not sure what to do here, ask your teaching team.
{% endif %}
