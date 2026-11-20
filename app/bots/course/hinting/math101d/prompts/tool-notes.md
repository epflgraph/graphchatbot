MATH-101d usage notes (strategy):
- For exercises and exams, leave query="" and rely on filters only.
- Weekly exercises are indexed as series: when the student names a series, use subtype "serie" with the series number and the exercise within it. Numbers are written without leading zeros: "S02" → number 2.
- A graded exercise to hand in ("exercice à rendre", "exercice rendu", homework) uses subtype "homework" with its number only — never pass sub_number there.
- For a question of the examen blanc (mock midterm), use subtype "midterm_exam" and always pass sub_number, the question number without any letter.
- The weekly lecture notes ("notes de la semaine N") are subtype "theory_slides": put "Notes Semaine N" in the query.

Examples (from text to filters):
- "S02 exo 3f": query="", filters={type:"practice", subtype:"serie", number:2, sub_number:3}
- "Série 11 exercice 1": query="", filters={type:"practice", subtype:"serie", number:11, sub_number:1}
- "Exercice rendu 1": query="", filters={type:"practice", subtype:"homework", number:1}
- "Examen blanc question 8": query="", filters={type:"exam", subtype:"midterm_exam", sub_number:8}
- "Notes du cours de la semaine 4": query="Notes Semaine 4", filters={type:"theory", subtype:"theory_slides"}
- "Critère de Cauchy pour les suites": query="critère de Cauchy suites convergence", filters={type:"theory"}
- "Comment montrer qu'une série converge ?": query="convergence séries numériques critères", filters={type:"theory"}
- "Théorème des valeurs intermédiaires": query="théorème des valeurs intermédiaires continuité", filters={type:"theory"}
