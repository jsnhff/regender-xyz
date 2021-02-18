# imports
import bisect # used to insert an element in a sorted list
import random # for the generation of the unique IDs while still keeping them easy to read by humans
from aux.nlp_helper import find_the_best_replacement_word, add_character_as_a_named_entity, find_protagonist_coreference_cluster, find_all_protagonist_coreferences, regender_paragraph, find_word_indices_in_paragraph # load auxiliary functions to help regendering words,
from classes.Protagonist import Protagonist

def regender_logic(nlp, paragraph, protagonist):

    ###############################
    #### START PARAGRAPH LOGIC ####
    ###############################

    # count how many times we expect the protagonist's name to occur in the current paragraph
    name_count = paragraph.count(protagonist.get_name())

    replacement_name = protagonist.get_replacement_name()
    is_female = protagonist.get_is_female()
    text_id = protagonist.get_text_id()
    gendered_pronouns = protagonist.get_gendered_pronouns()

    if replacement_name in paragraph:
        # change the other character's name to something different
        paragraph = paragraph.replace(replacement_name, protagonist.get_other_character_replacement_name())

    # find all coreferences of the protanogist in this paragraphs
    doc = nlp(paragraph)
    has_found_corefs = doc._.has_coref
    print("-------")

    print(doc._.coref_clusters)

    # find all non-protagonist proper names in the paragraph
    paragraph_proper_names, paragraph_proper_name_indices = find_word_indices_in_paragraph(doc.ents, True)

    if has_found_corefs and name_count < 1: # ERROR HANDLING
        print('\nCAUTION: we have found co-references to the name of the main protagonist is this paragraph, where there should be any....')
        regendered_paragraph = paragraph
    else:
        # iterate over the co-reference CLUSTERS found and SELECT ONLY the one with the name of the protagonist
        additional_character = None
        character = protagonist.character_1
        if character != '': # in case no additional character name has been given in the config.ini file
            additional_character = character
        doc = find_protagonist_coreference_cluster(nlp, doc, paragraph, protagonist, additional_character)

        protagonist_coreference_words, protagonist_coreference_indices = find_word_indices_in_paragraph(doc._.coref_clusters, False)
        print('Coreference clusters -> ', doc._.coref_clusters)
        print(protagonist_coreference_indices, paragraph_proper_names, "Proper Name Indices ->", paragraph_proper_name_indices)

        # remove the protagonist index from the paragraph's proper name indices
        paragraph_proper_name_indices = [x for x in paragraph_proper_name_indices if x not in protagonist_coreference_indices]
        print('----------')

        first_occurrence_next_proper_name = paragraph_proper_name_indices[0] # stop protagonist cluster here

        index_to_stop_protagonist_coreferences = bisect.bisect_left(protagonist_coreference_indices, first_occurrence_next_proper_name)
        paragraph_index_to_stop_protagonist_coreferences = protagonist_coreference_indices[index_to_stop_protagonist_coreferences]

        # clean the protagonist's coreference cluster -> e.g when the protagonist is a woman but we have coreferences such as 'he' and 'him'
        reference_dict = find_all_protagonist_coreferences(doc, gendered_pronouns)

        # remove coreference which we think link to other proper names / not protagonist's ones
        # e.g. remove dict keys which are not in the list
        for key in list(reference_dict.keys()):
            if key >= paragraph_index_to_stop_protagonist_coreferences:
                reference_dict.pop(key)

        print('\n\n')
        # regender paragraph
        regendered_paragraph = regender_paragraph(text_id, doc, protagonist, is_female, reference_dict)

    return regendered_paragraph

    ##############################
    #### END PARAGRAPH LOGIC #####
    ##############################

def save_regendered_paragraph(regendered_paragraph, output_file):
    print(regendered_paragraph)
    ## write the regendered paragraph to file
    with open(output_file, 'a') as fp:
        fp.write("\n")
        fp.write(regendered_paragraph)
    print('--------------------------------------------------------, Next paragraph...')