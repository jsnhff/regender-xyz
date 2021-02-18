import spacy # the NLP library we use
import neuralcoref # the coreference resolution add-on to the NLP library we use
import pandas as pd
import configparser # to read the variable values from the config file
import subprocess, os
import gdown

# get the GIT root folder, e.g. the root folder of the project
root_dir = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True).stdout.decode('utf-8').rstrip()

# read variables from a CONFIG FILE
configfile_name = root_dir + os.sep + "config.ini"
config = configparser.ConfigParser()
config.read(configfile_name)

# reading FIXED variables
MALE_PRONOUNS = config.get('pronouns', 'MALE').split('|||')
FEMALE_PRONOUNS = config.get('pronouns', 'FEMALE').split('|||')
# END of reading FIXED variables

def get_root_folder():
    root_path = None
    stream = os.popen("git rev-parse --show -toplevel") # prints the absolute path to the root folder of the git repo on your local mahcine
    root_path = stream.read()
    return root_path

def load_spacy_neuralcoref():
    # load needed language resources
    nlp = spacy.load('en')
    neuralcoref.add_to_pipe(nlp)

    # load Spacy's entity ruler which allows for manual annotation of Named Entities
    ruler = nlp.create_pipe("entity_ruler")

    return nlp, ruler

def load_exceprt_data(text_id):

    # get the file with the text from config.ini
    TEXT_FILE = config.get(text_id, 'TEXT_FILE')
    TEXT_FILE_SHEET = config.get(text_id, 'TEXT_FILE_SHEET')

    if TEXT_FILE_SHEET != 'None':
        TEXT_FILE = root_dir + os.sep + TEXT_FILE
        SHEET_LINE = int(config.get(text_id, 'SHEET_LINE')) # as we originally read it as a STR from config.ini
        excerpts = pd.read_excel(TEXT_FILE, TEXT_FILE_SHEET)
        text = excerpts.loc[SHEET_LINE].Paragraph
        protagonist = excerpts.loc[SHEET_LINE].Character
        gender = excerpts.loc[SHEET_LINE].Gender
    else:
        local_file = root_dir + os.sep + 'data' + os.sep + text_id + '.txt'
        if not os.path.exists(local_file): # local_file DOES NOT exist, download
            gdown.download(TEXT_FILE, local_file, quiet=False)
        else:
            print('This file', local_file, 'seems to has been downloaded. Skipping Gdrive download.')
            print('\n')

        text = None # we stream the reading of the txt file by reading a paragraph at a time
        protagonist = config.get(text_id, 'PROTAGONIST_NAME')
        gender = config.get(text_id, 'PROTAGONIST_GENDER')

    if gender.lower() == 'female':
        is_female = True
    else:
        is_female = False

    gendered_pronouns = None
    if is_female:
        gendered_pronouns = FEMALE_PRONOUNS
    else:
        gendered_pronouns = MALE_PRONOUNS

    return text, protagonist, gender, is_female, gendered_pronouns