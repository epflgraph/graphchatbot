{% if lang_code == 'fr' %}
Cette session porte uniquement sur **{{ topic.name }}**, et elle se termine une fois que tu l'as expliqué et montré que cela tient ; pas avant.

Reprends ton explication là où tu t'es arrêté. Si tu bloques, dis quelle partie n'est pas claire et nous partirons de là.
{% elif lang_code in ['de', 'gsw'] %}
In dieser Sitzung geht es ausschliesslich um **{{ topic.name }}**, und sie endet erst, wenn du das Thema erklärt und belegt hast; nicht vorher.

Fahr dort fort, wo du aufgehört hast. Wenn du nicht weiterkommst, sag, welcher Teil unklar ist, und wir beginnen dort.
{% elif lang_code == 'it' %}
Questa sessione riguarda solo **{{ topic.name }}**, e finisce una volta che l'avrai spiegato e dimostrato che regge; non prima.

Riprendi la spiegazione da dove l'hai lasciata. Se ti blocchi, dimmi quale parte non è chiara e partiremo da lì.
{% else %}
This session is only about **{{ topic.name }}**, and it finishes once you have explained it and shown that it holds up; not before.

Carry on explaining it from where you left off. If you are stuck, say which part is unclear and we will work from there.
{% endif %}
