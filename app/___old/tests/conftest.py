tool_inputs = {
    'search_nodes': [
        {'keywords': ["solar cells"], 'node_type': 'Person'},
        {'keywords': ["data science"], 'node_type': ['Lecture', 'Course', 'MOOC']},
        {'keywords': ["lidar"], 'node_type': 'Startup'},
        {'keywords': ["nuclear fusion"], 'node_type': ['Publication', 'Unit', 'Startup']},
    ],
    'search_exercises': [
        {'query': "derivatives"},
        {'query': "oscillators"},
        {'query': "angular velocity"},
    ],
    'search_news': [
        {'query': "Anna Fontcuberta"},
    ],
    'search_plan': [
        {'query': "CM 1 105"},
    ],
}

end_to_end_prompts = [
    "what do you know about Patrick Jermann?",
    "hey show me people doing research on sustainable urbanism",
    "hey show me exercises about magnetic fields",
    "hey show me news about CEDE",
]
