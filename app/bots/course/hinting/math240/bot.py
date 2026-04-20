from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.bots.course.bot import HintingCourseBot


class TheoryFilters(BaseModel):
    type: Literal["theory"]
    subtype: Optional[Literal["lecture_slides", "textbook"]] = Field(
        default=None,
        description="Optional subtype for theory content.",
    )


class PracticeFilters(BaseModel):
    type: Literal["practice"]
    subtype: Optional[Literal["serie"]] = Field(
        default=None,
        description="Optional subtype for practice content.",
    )
    number: Optional[str] = Field(
        default=None,
        description="Serie number, e.g. 'Série 4' → '4'.",
    )


class ToolInput(BaseModel):
    """
    Search schema for MATH-240 course material.
    Keep queries concise (≤ 15 words). For exercises leave query="" and rely on filters.
    """
    query: str = Field("", description="Concise keywords (≤15 words).")
    filters: Annotated[Union[TheoryFilters, PracticeFilters], Field(discriminator="type")] = Field(
        default_factory=lambda: TheoryFilters(type="theory"),
        description="Strict, per-type filters (discriminated by 'type').",
    )


COURSE_DETAILS = """
# Statistique

## Course information

- **Code:** MATH-240
- **Crédits:** 5
- **Enseignant:** [Panaretos Victor](https://people.epfl.ch/180565?lang=en)
- **Langue:** Français

## Résumé

Ce cours donne une introduction au traitement mathématique de la théorie de l'inférence statistique en utilisant la notion de vraisemblance comme un thème central.

## Contenu

- Modèles de probabilité, variables aléatoires, données, et paramètres.
- Théorèmes limites élémentaires de probabilité et leur combinaison.
- Problèmes d'inférence statistique : estimation ponctuelle, estimation par intervalle, tests.
- Statistiques et leurs critères de performance (consistance, concentration, biais, variance).
- L'estimation en tant que probabilité inverse et la fonction de vraisemblance comme thème unificateur.
- Principes d'exhaustivité et de vraisemblance (réduction de données, théorème de Fisher-Neyman).
- Théorie de la vraisemblance pour l'estimation (propriétés pour des échantillons de taille finie, relation avec l'exhaustivité et le non-biais, borne de Cramér-Rao, optimalité asymptotique, exemples).
- Autres méthodes d'estimation ponctuelle (méthode des moments, méthode du plug-in, exemples).
- Théorie de la vraisemblance pour l'estimation d'intervalle (intervalles exacts et asymptotiques, pivots).
- Théorie de la vraisemblance pour les tests (cadre de Neyman–Pearson, tests du rapport de vraisemblance).

## Acquis de formation

À la fin de ce cours, l'étudiant doit être capable de :
- Exploiter les résultats de base en probabilité pertinents pour l'inférence statistique.
- Formaliser le cadre théorique des trois principaux problèmes en inférence statistique.
- Évaluer la performance de procédures statistiques à l'aide de critères rigoureux.
- Dériver des estimateurs ponctuels, des intervalles de confiance et des tests d'hypothèse à partir de principes généraux.

## Méthode d'évaluation

Examen écrit.

## Ressources

### Liens Moodle
- https://go.epfl.ch/MATH-240

## In the programs

**Mathematics** — Bachelor semester 4, Spring, Mandatory.

## Reference week

- **Monday, 10:00–12:00:** Exercise — CM5
- **Tuesday, 13:00–15:00:** Lecture — AAC231"""


class MATH240Bot(HintingCourseBot):
    name = 'MATH-240'
    index = 'course_math240'
    groups = ['graph-chatbot-admins', 'graph-rag-vip', 'chatbot_math_240']

    course_name = 'MATH-240: Statistics'
    course_details = COURSE_DETAILS
    tool_input_schema = ToolInput
