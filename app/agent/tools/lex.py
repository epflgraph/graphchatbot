"""
This module contains the tool to do RAG in the lex index.
"""

from typing import Optional, Literal

from app.interfaces.graphai import GraphAIClient


def search_lex(query: str, lang: Optional[Literal['en', 'fr']] = None, limit: Optional[int] = 10) -> list:
    """
    Performs a search in the current legal documents of EPFL about rules and regulations. It searches in the given `lang` (or in all languages if unspecified) and returns up to `limit` results.
    The `query` parameter should be a natural language description of what the user requests.
    """

    print("[LEX TOOL]", f"Called the `search_lex` tool with input=`{query}`, lang=`{lang}` and limit=`{limit}`")

    # Return empty if input is empty
    if not query:
        return []

    gac = GraphAIClient()

    # Prepare payload
    payload = {
        'index': 'lex',
        'text': query,
        'lang': lang,
        'limit': limit
    }

    # Send request and return empty if it fails
    try:
        response = gac.call_sync_endpoint(endpoint='/rag/retrieve', payload=payload)
    except Exception as e:
        print("[LEX TOOL]", f"Error retrieving lex document chunks: {e}")
        return []

    # Return empty if response is not marked as successful
    if not response.get('successful'):
        print("[LEX TOOL]", f"Unsuccessful retrieval of lex chunks: {response.get('result', [])}")
        return []

    return response.get('result', [])


if __name__ == '__main__':
    from collections import Counter

    questions = [
        "How many holidays do EPFL workers have?",
        "What is the recruitment process for faculty and research positions at EPFL?",
        "What are the eligibility criteria for international candidates applying for jobs?",
        "What are the salary ranges for different academic and administrative positions?",
        "How does EPFL handle work permits and visas for non-Swiss employees?",
        "What are the standard employee benefits at EPFL (health insurance, pension, vacation days, etc.)?",
        "How does the EPFL pension scheme work?",
        "Are there any special benefits for PhD students and postdocs?",
        "What is the parental leave policy at EPFL?",
        "How does EPFL handle remote or hybrid work arrangements?",
        "How are employment contracts structured at EPFL (fixed-term, permanent, etc.)?",
        "What is the process for contract renewal or extension?",
        "How does EPFL handle probation periods for new employees?",
        "What are the working hour regulations for administrative and research staff?",
        "What professional development programs does EPFL offer for employees?",
        "Are there language courses available for non-French/German speakers?",
        "How does EPFL support career progression for academic and non-academic staff?",
        "How can an employee report workplace harassment or discrimination?",
        "What are the policies on conflict resolution and mediation at EPFL?",
        "How does EPFL handle employee grievances and disputes?"
    ]

    results = []
    for question in questions:
        results += search_lex(query=question, lang='en', limit=10)

    files = [result['name'] for result in results]
    counter = Counter(files)

    print(counter)

    ################################################################

    keyphrases = [
        "EPFL recruitment process",
        "Job application at EPFL",
        "Eligibility criteria for international candidates",
        "Salary ranges for academic and administrative positions",
        "Work permits and visas for non-Swiss employees",
        "EPFL employee benefits (health insurance, pension, vacation days)",
        "EPFL pension scheme",
        "Special benefits for PhD students and postdocs",
        "EPFL parental leave policy",
        "Remote and hybrid work arrangements at EPFL",
        "EPFL employment contracts (fixed-term, permanent)",
        "Contract renewal and extension process",
        "Probation periods for new employees",
        "Working hour regulations for administrative and research staff",
        "Professional development programs at EPFL",
        "Language courses for non-French/German speakers",
        "Career progression support at EPFL",
        "Reporting workplace harassment and discrimination",
        "Conflict resolution and mediation policies at EPFL",
        "Employee grievances and dispute resolution at EPFL"
    ]

    results = []
    for keyphrase in keyphrases:
        results += search_lex(query=keyphrase, lang='en', limit=10)

    files = [result['name'] for result in results]
    counter = Counter(files)

    print(counter)
