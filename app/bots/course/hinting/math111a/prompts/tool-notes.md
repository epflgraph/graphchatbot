MATH-111a usage notes (strategy):
- For exercises and exams, leave query="" and rely on filters only.
- Weekly exercises are indexed as series: when the student names a series, use subtype "serie" with the series number and the exercise within it.
- Standalone exercises (e.g. "Question ouverte") use subtype "exercise" with the exercise number only — never pass sub_number there.
- For an exercise or question from an exam, pass sub_number with the exercise/question number only and discard any letter, and when an academic year is indicated use its first year for number (e.g. 2018/2019 → 2018).

Examples (from text to filters):
- "Examen 2022/2023 exercise 14b": query="", filters={type:"exam", number:"2022", sub_number:"14"}
- "Examen 2019 question 3": query="", filters={type:"exam", number:"2019", sub_number:"3"}
- "Exercice 1 de la série 1": query="", filters={type:"practice", subtype:"serie", number:"1", sub_number:"1"}
- "Question ouverte 4": query="", filters={type:"practice", subtype:"exercise", number:"4"}
- "Chapitre 4 - Espaces vectoriels": query="Chapitre 4 - Espaces vectoriels", filters={type:"theory"}
- "Diagonalisation d'une matrice": query="Diagonalisation matrice valeurs propres", filters={type:"theory"}
