import json
import Levenshtein

import numpy as np
import pandas as pd

import tiktoken

from app.interfaces.db import get_db_manager

################################################################


def remove_repetitive_patterns(content):
    """
    Remove repetitive patterns detected manually on the data.
    """

    # List of identified patterns
    known_patterns = ['o ', 'oo', 'Ã Â ', 'Ã ', 'Â ', 'no, ', '• ', '<br>', "it's... ", '====', '....', '····', '----', 'okay, ', '""""', '1. ', ' -1.', '3, 3, ', '--- ', 'N ', 'N.', 'p ', '____', ', yeah', 'yeah, ', '< ', 'sr. ', 'zo. ', 'RT ', 'I-', 'ah ', 'la-', 'grand ', 'la même chose que ', 'des ', 'from ', 'par ', " C\'est vrai", ' " C\'est', 'x ', 'yes, ', 'O ', '0. ', '0 0 ', '0000', 'OOO.', 'FFFF', 'EEEE', '::::', '▬▬▬▬', '……', '/t/t', 'H: ', '= ', 'rt ', 'très ', ' et "B"']

    # Look for repetitions of these patterns and collapse them
    clean_contents = []
    for content in content:
        for pattern in known_patterns:
            while (pattern + pattern) in content:
                content = content.replace(pattern + pattern, pattern)

        clean_contents.append(content)

    return clean_contents


def fetch_lecture_metadata(lecture_id):
    # Fetch lecture metadata
    table = 'graph_lectures.Nodes_N_Lecture'
    fields = ['original_title', 'original_description', 'original_tags']
    columns = ['title', 'description', 'keywords']
    conditions = {'institution_id': 'EPFL', 'object_type': 'Lecture', 'object_id': lecture_id}
    lecture = pd.DataFrame(get_db_manager().db.find(table_name=table, fields=fields, conditions=conditions), columns=columns)

    # For each field, make a list with the different values across the lecture videos
    metadata = {}
    for column in columns:
        values = list(lecture[column].dropna())

        # We assume there is either 0 or 1 matches, since we fix the primary key
        if values:
            [metadata[column]] = values

    return metadata


def fetch_lecture_slides(lecture_id):
    # Fetch lecture slides
    table = 'graph_lectures.Edges_N_Lecture_N_Slide_T_ParentToChild'
    fields = ['to_object_id', 'sort_number']
    columns = ['slide_id', 'slide_number']
    conditions = {'from_institution_id': 'EPFL', 'from_object_type': 'Lecture', 'from_object_id': lecture_id, 'to_institution_id': 'EPFL', 'to_object_type': 'Slide'}
    lecture_slides = pd.DataFrame(get_db_manager().db.find(table_name=table, fields=fields, conditions=conditions), columns=columns)
    slide_ids = list(lecture_slides['slide_id'])

    # Return if no slides
    if len(lecture_slides) == 0:
        return []

    # Fetch Slide nodes
    table = 'graph_lectures.Nodes_N_Slide'
    fields = ['object_id', 'text_original', 'text_en']
    columns = ['slide_id', 'slide_text', 'slide_text_en']
    conditions = {'institution_id': 'EPFL', 'object_type': 'Slide', 'object_id': slide_ids}
    slides = pd.DataFrame(get_db_manager().db.find(table_name=table, fields=fields, conditions=conditions), columns=columns)

    # Merge them in the same DataFrame to add the slide number and sort
    slides = pd.merge(lecture_slides, slides, how='inner', on='slide_id')
    slides = slides.sort_values('slide_number')

    # Fill with text_en whenever text_original is not available
    slides['slide_text'] = slides['slide_text'].replace('', None).fillna(slides['slide_text_en'])

    # Remove empty slides, drop duplicates and convert to list of strings
    slides = slides[slides['slide_text'] != '']
    slides = list(slides['slide_text'].drop_duplicates())

    # Pre-process slides: Remove None values and empty strings
    slides = [slide for slide in slides if slide is not None]
    slides = [slide.strip() for slide in slides if slide.strip()]

    # Remove repetitive patterns
    slides = remove_repetitive_patterns(slides)

    return slides


def fetch_lecture_transcripts(lecture_id):
    # Fetch lecture transcripts
    table = 'graph_lectures.Edges_N_Lecture_N_Transcript_T_ParentToChild'
    fields = ['to_object_id', 'sort_number']
    columns = ['transcript_id', 'transcript_number']
    conditions = {'from_institution_id': 'EPFL', 'from_object_type': 'Lecture', 'from_object_id': lecture_id, 'to_institution_id': 'EPFL', 'to_object_type': 'Transcript'}
    lecture_transcripts = pd.DataFrame(get_db_manager().db.find(table_name=table, fields=fields, conditions=conditions), columns=columns)
    transcript_ids = list(lecture_transcripts['transcript_id'])

    # Return if no transcripts
    if len(lecture_transcripts) == 0:
        return []

    # Fetch Transcript nodes
    table = 'graph_lectures.Nodes_N_Transcript'
    fields = ['object_id', 'text_original', 'text_en']
    columns = ['transcript_id', 'transcript_text', 'transcript_text_en']
    conditions = {'institution_id': 'EPFL', 'object_type': 'Transcript', 'object_id': transcript_ids}
    transcripts = pd.DataFrame(get_db_manager().db.find(table_name=table, fields=fields, conditions=conditions), columns=columns)

    # Merge them in the same DataFrame to add the transcript number and sort
    transcripts = pd.merge(lecture_transcripts, transcripts, how='inner', on='transcript_id')
    transcripts = transcripts.sort_values('transcript_number')

    # Fill with text_en whenever text_original is not available
    transcripts['transcript_text'] = transcripts['transcript_text'].str.strip().replace('', None).fillna(transcripts['transcript_text_en'])

    # Remove empty transcripts, drop duplicates and convert to list of strings
    transcripts = transcripts[transcripts['transcript_text'] != '']
    transcripts = list(transcripts['transcript_text'].drop_duplicates())

    # Pre-process transcripts: Remove None values, empty strings and "subtitles generated automatically"
    transcripts = [transcript for transcript in transcripts if transcript is not None]
    transcripts = [transcript.replace("These subtitles have been generated automatically", '') for transcript in transcripts]
    transcripts = [transcript.replace("Ces sous-titres ont été générés automatiquement", '') for transcript in transcripts]
    transcripts = [transcript.strip() for transcript in transcripts if transcript.strip()]

    # Remove repetitive patterns
    transcripts = remove_repetitive_patterns(transcripts)

    return transcripts


################################################################

def count_tokens(text, model_name):
    if not isinstance(text, str):
        text = json.dumps(text)

    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(text))


def prune_content(content, model_name, context_window_size=128000, token_padding=0, lev_ratio_threshold=0.9):
    """
    Computes the Levenshtein ratios between all pairs of content pieces, then iteratively deletes those that are most redundant, until either
    there is only one or both all differences are below the given threshold and the whole token count is below the context window size.
    Observation: This function uses tiktoken for token counting, which has been reported to underestimate the actual token count.
    Hence, the token count of the output of this function is an estimation and still could exceed the actual context window in some cases.
    """

    # Return if no content
    if not content:
        return content

    # Return if no context window
    context_window_size -= token_padding
    if context_window_size <= 0:
        return []

    # Compute Levenshtein ratios between all pairs of text pieces
    n = len(content)
    ratios = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            ratio = Levenshtein.ratio(content[i], content[j])
            ratios[i, j] = ratio
            ratios[j, i] = ratio

    # Get the initial number of tokens of user prompt
    user_tokens = count_tokens(content, model_name)

    # Iterate and remove one slide at a time while there are still eligible ones
    max_lev_ratio = ratios.max()
    while n > 1 and (max_lev_ratio >= lev_ratio_threshold or user_tokens > context_window_size):
        # Get indices of max value
        i, j = np.unravel_index(ratios.argmax(), ratios.shape)

        # Decide which one to delete, either i or j. We delete k, the one with the second-highest max levenstein ratio.
        ratios[i, j] = 0
        ratios[j, i] = 0
        if ratios[i].max() > ratios[j].max():
            k = i
        else:
            k = j

        # Delete row and column from ratios matrix and recompute max
        ratios = np.delete(ratios, k, axis=0)
        ratios = np.delete(ratios, k, axis=1)
        max_lev_ratio = ratios.max()

        # Delete text from content pieces list and recompute n
        content = content[:k] + content[(k + 1):]
        n = len(content)

        # Recompute user tokens
        user_tokens = count_tokens(content, model_name)

    return content
