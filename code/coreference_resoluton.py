# imports
import bisect # used to insert an element in a sorted list
import random # for the generation of the unique IDs while still keeping them easy to read by humans
import configparser # to read the variable values from the config file
import subprocess, os

from aux.nlp_helper import find_the_best_replacement_word, add_character_as_a_named_entity, find_protagonist_coreference_cluster, find_all_protagonist_coreferences, regender_paragraph, find_word_indices_in_paragraph # load auxiliary functions to help regendering words,
from aux.load import load_spacy_neuralcoref, load_exceprt_data # load auxiliary functions to load NLP libraries & data

# get the GIT root folder, e.g. the root folder of the project
root_dir = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True).stdout.decode('utf-8').rstrip()

# read variables from a CONFIG FILE
configfile_name = root_dir + os.sep + "config.ini"
config = configparser.ConfigParser()
config.read(configfile_name)

# indicator to find the text we regender
FIND_TEXT = config.get('quotes', 'OPENING').split('|||')

## get the output folder
OUTPUT_FOLDER = config.get('folders', 'OUTPUT_FOLDER')

# we want to avoid regendering all coreferences which are between quotation marks
OPENING_QUOTES = config.get('quotes', 'OPENING').split('|||')
CLOSING_QUOTES = config.get('quotes', 'CLOSING').split('|||')
inside_dialog = False

# detect the gender
is_female = True

# load needed language resources
nlp, ruler = load_spacy_neuralcoref()

# load the text
### choose between one of the following options
# for Pride and Prejudice -> prideandprejudice
# for Beloved -> beloved
# for Harry Potter -> harrypotter
# for Rabbit Run -> rabbitrun
# for the Sound and Fury -> thesoundandfury
### END
text_id = 'harrypotter'
text, protagonist, gender, is_female, gendered_pronouns = load_exceprt_data(text_id)

PROTAGONIST_REPLACEMENT_NAME = config.get(text_id, 'PROTAGONIST_REPLACEMENT_NAME')
OTHER_CHARACTER_SAME_NAME_CHANGE = config.get(text_id, 'OTHER_CHARACTER_SAME_NAME_CHANGE')
CHARACTER = config.get(text_id, 'CHARACTER_1')
output_file = root_dir + os.sep + OUTPUT_FOLDER + os.sep + text_id + "_regendered.txt"

# Creates an empty file as  output_file
with open(output_file, 'w') as fp:
    pass

#####################
#### START LOGIC ####
#####################

# in case spacy does not regognize the protanogist's name we have as a Named Entity, add it manually
print('--------')
ruler = add_character_as_a_named_entity(nlp, protagonist, ruler)
ruler = add_character_as_a_named_entity(nlp, CHARACTER, ruler)
nlp.add_pipe(ruler)

# a. split the excerpt into paragraphs when the char sequence \n\n is detected
paragraphs = text.split('\n\n')
print('There are', len(paragraphs), 'paragraphs detected.')
print("-------")

# assign unique ids for the pronouns of the coreferences in the protagonist's cluster
unique_id = random.randint(1000, 9999) # select at random a 4-digit number

# b. find the references to the protagonist in each paragraph
para_count = 1

for paragraph in paragraphs:

    # count how many times we expect the protagonist's name to occur in the current paragraph
    name_count = paragraph.count(protagonist)

    if PROTAGONIST_REPLACEMENT_NAME in paragraph:
        # change the other character's name to something different
        paragraph = paragraph.replace(PROTAGONIST_REPLACEMENT_NAME, OTHER_CHARACTER_SAME_NAME_CHANGE)

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
        if CHARACTER != '': # in case no additional character name has been given in the config.ini file
            additional_character = CHARACTER
        doc = find_protagonist_coreference_cluster(nlp, doc, paragraph, protagonist, is_female, gendered_pronouns, additional_character)

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
        regendered_paragraph = regender_paragraph(text_id, doc, protagonist, is_female, unique_id, reference_dict)

    print(regendered_paragraph)
    ## write the regendered paragraph to file
    with open(output_file, 'a') as fp:
        fp.write("\n")
        fp.write(regendered_paragraph)

    print('--------------------------------------------------------, Next paragraph...')

    para_count += 1

#####################
##### END LOGIC #####
#####################
