MATH-111e usage notes (strategy):
- For exercises and exams, leave query="" and rely on filters only.
- Weekly exercises are indexed as series: when the student names a series, use subtype "serie" with the series number and the exercise within it.
- Exercises to hand in ("exercice à rendre", "question à rendre", homework) use subtype "homework" with the homework number only — never pass sub_number there.
- The midterm ("examen blanc") is exam number 1: pass sub_number with the question number only and discard any letter.
- Numbers are written without leading zeros: "S02" → number 2.
- The weekly lecture notes ("notes de la semaine N") are subtype "theory_slides": put "Notes Semaine N" in the query.
- The course material is in French: write the query in French even when the student writes in English, e.g. "eigenvalues" → "valeurs propres".

Examples (from text to filters):
- "Examen blanc question 8b": query="", filters={type:"exam", subtype:"midterm_exam", number:1, sub_number:8}
- "S02 exo 3f": query="", filters={type:"practice", subtype:"serie", number:2, sub_number:3}
- "Série 11 exercice 1": query="", filters={type:"practice", subtype:"serie", number:11, sub_number:1}
- "Exercice à rendre 2": query="", filters={type:"practice", subtype:"homework", number:2}
- "Notes du cours de la semaine 4": query="Notes Semaine 4", filters={type:"theory", subtype:"theory_slides"}
- "Chapitre 4 - Espaces vectoriels": query="Chapitre 4 - Espaces vectoriels", filters={type:"theory"}
- "Diagonalisation d'une matrice": query="Diagonalisation matrice valeurs propres", filters={type:"theory"}
- "Comment calculer un déterminant 3x3 ?": query="déterminant matrice 3x3 calcul", filters={type:"theory"}
- "Il y a une vidéo du cours sur les déterminants ?": query="déterminant", filters={type:"theory", subtype:"mediaspace_video"}
