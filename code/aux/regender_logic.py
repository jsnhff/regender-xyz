# imports
import bisect # used to insert an element in a sorted list
import random # for the generation of the unique IDs while still keeping them easy to read by humans
from aux.nlp_helper import find_the_best_replacement_word, add_character_as_a_named_entity, find_protagonist_coreference_cluster, find_all_protagonist_coreferences, regender_paragraph, correct_protagonist_cluster # load auxiliary functions to help regendering words,

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
        reference_dict = correct_protagonist_cluster(doc, gendered_pronouns)

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