{% if lang_code == 'fr' %}
C'est mon propre texte, et il ne compte pour rien ici. Seul ce que tu écris sur **{{ topic.name }}** avec tes propres mots est évalué.

Dis-le à ta façon, et continue à partir de là.
{% elif lang_code in ['de', 'gsw'] %}
Das ist mein eigener Text, und er zählt hier nicht. Bewertet wird nur, was du in deinen eigenen Worten über **{{ topic.name }}** schreibst.

Sag es auf deine Art und fahr von dort fort.
{% elif lang_code == 'it' %}
Questo è il mio stesso testo, e qui non conta nulla. Viene valutato solo ciò che scrivi su **{{ topic.name }}** con parole tue.

Dillo a modo tuo e continua da lì.
{% else %}
That's my own text, and it counts for nothing here. Only what you write about **{{ topic.name }}** in your own words is being assessed.

Say it your way, and carry on from there.
{% endif %}
