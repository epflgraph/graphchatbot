tool_inputs = {
    'search_nodes': [
        {'query': "solar cells", 'node_type': 'Person'},
        {'query': "data science", 'node_type': ['Lecture', 'Course', 'MOOC']},
        {'query': "lidar", 'node_type': 'Startup'},
        {'query': "nuclear fusion", 'node_type': ['Publication', 'Unit', 'Startup']},
    ],
    'search_exercises': [
        {'query': "derivatives"},
        {'query': "oscillators"},
        {'query': "angular velocity"},
    ],
    'search_news': [
        {'query': "Anna Fontcuberta"},
    ],
}

end_to_end_prompts = [
    "hey show me people doing research on sustainable urbanism",
    "hey show me exercises about magnetic fields",
    "hey show me news about CEDE",
]
