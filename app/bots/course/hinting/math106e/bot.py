from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "polycopie", "resume", "proof", "recommended_reading"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie", "serie_entrainement", "qcm"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="When subtype is 'serie' or 'serie_entrainement': serie number N. When subtype is 'qcm': e.g. 'QCM Q3' → 'Q3'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="When subtype is 'serie': exercise number, e.g. 'Série 3 Exercice 4' → '4'. When subtype is 'serie_entrainement': always N.M format, e.g. 'exo 3.1' → '3.1'.",
    )


class ExamFilters(BaseModel):
    type: Literal["exam"]
    subtype: Optional[Literal["previous_year_exam", "mock_exam"]] = Field(
        default=None,
        description="e.g. 'Examen 2019' → 'previous_year_exam', 'Test blanc' → 'mock_exam'.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Year of the exam, e.g. 'Exam 2022' → '2022'.",
    )
    sub_number: Optional[str] = Field(
        default=None,
        description="Exercise number within the exam, e.g. 'Examen 2024 Q15' → '15'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-106(e) course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters, ExamFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


COURSE_DETAILS = """
# Analyse II

## Informations générales

- **Code :** MATH-106(e)
- **Coefficient :** 6
- **Enseignant :** [Lachowska Anna](https://people.epfl.ch/167946?lang=fr)
- **Langue :** Français

## Résumé

Étudier les concepts fondamentaux d'analyse et le calcul différentiel et intégral des fonctions réelles de plusieurs variables.

## Contenu

- L'espace ℝⁿ
- Calcul différentiel des fonctions à plusieurs variables
- Intégrales multiples
- Équations différentielles ordinaires
- Méthodes de démonstration et arguments mathématiques

## Acquis de formation

- Appliquer avec aisance les compétences acquises en Analyse I
- Maîtriser le calcul différentiel et intégral des fonctions de plusieurs variables
- Maîtriser les équations différentielles élémentaires

## Méthode d'évaluation

Examen écrit

## Ressources

### Liens Moodle
- https://go.epfl.ch/MATH-106_e

### Vidéos
- https://mediaspace.epfl.ch/channel/MATH-106%2528e%2529%2BAnalyse%2BII%2BIN_SC/30437

## Plans d'études

**Informatique** — Bachelor semestre 2, Printemps, Obligatoire.
**Systèmes de communication** — Bachelor semestre 2, Printemps, Obligatoire.

## Semaine de référence

- **Lundi, 10h–12h:** Cours — CO1
- **Mercredi, 10h–12h:** Cours — CO1
- **Jeudi, 10h–12h:** Exercices / TP"""

RETRIEVAL_NOTES = """\
When the subtype is 'serie_entrainement', the sub_number MUST follow the N.M pattern:
- 'Série entrainement 1, Q1.4' → subtype='serie_entrainement', number='1', sub_number='1.4'
- 'Série entrainement 2, exo 1.1' → subtype='serie_entrainement', number='2', sub_number='1.1'
- 'Série entrainement 1, 2ème QCM exo 1' → subtype='serie_entrainement', number='1', sub_number='2.1'"""


class MATH106eBot(HintingCourseBot):
    name = 'MATH-106e'
    index = 'course_math106e'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_math_106_e']

    course_name = 'MATH-106(e): Analyse II'
    course_details = COURSE_DETAILS
    tool_input_schema = ToolInput

    @property
    def retrieval_notes(self) -> str:
        return RETRIEVAL_NOTES
