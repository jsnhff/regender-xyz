# imports
import random # for the generation of the unique IDs while still keeping them easy to read by humans
import configparser # to read the variable values from the config file
import subprocess, os

from aux.nlp_helper import add_character_as_a_named_entity
from aux.load import load_spacy_neuralcoref, load_exceprt_data # load auxiliary functions to load NLP libraries & data
from classes.Protagonist import Protagonist
from aux.regender_logic import regender_logic, save_regendered_paragraph

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
text_id = 'thesoundandfury'
text, protagonist_name, gender, is_female, gendered_pronouns = load_exceprt_data(text_id)

PROTAGONIST_REPLACEMENT_NAME = config.get(text_id, 'PROTAGONIST_REPLACEMENT_NAME')
OTHER_CHARACTER_SAME_NAME_CHANGE = config.get(text_id, 'OTHER_CHARACTER_SAME_NAME_CHANGE')
CHARACTER = config.get(text_id, 'CHARACTER_1')
output_file = root_dir + os.sep + OUTPUT_FOLDER + os.sep + text_id + "_regendered.txt"

protagonist = Protagonist(protagonist_name, is_female, gendered_pronouns, PROTAGONIST_REPLACEMENT_NAME, CHARACTER,
                 OTHER_CHARACTER_SAME_NAME_CHANGE, text_id)

# Creates an empty file as  output_file
with open(output_file, 'w') as fp:
    pass

# Creates an empty file as  output_file
with open(output_file, 'w') as fp:
    pass

para_count = 1
if text == None: # we are reading from a txt file -> the text tpo regender is long
    local_file = root_dir + os.sep + 'data' + os.sep + text_id + '.txt'
    with open(local_file, "r") as paragraphs_file:
        i = 0
        content = paragraphs_file.readlines()
        for paragraph in content:
            regendered_paragraph = regender_logic(nlp, paragraph, protagonist)
            save_regendered_paragraph(regendered_paragraph, output_file)
            para_count += 1
else: # we are reading text exceprts from an Excel sheet
    # a. split the excerpt into paragraphs when the char sequence \n\n is detected
    paragraphs = text.split('\n\n')
    print('There are', len(paragraphs), 'paragraphs detected.')
    print("-------")

    for paragraph in paragraphs:
        regendered_paragraph = regender_logic(nlp, paragraph, protagonist)
        save_regendered_paragraph(regendered_paragraph, output_file)
        para_count += 1
