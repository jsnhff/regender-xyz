import spacy # the NLP library we use
import neuralcoref # the coreference resolution add-on to the NLP library we use
import pandas as pd
import configparser # to read the variable values from the config file
import subprocess, os

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

# if i = 8, we load Pride and Prejudice excerpt
def load_exceprt_data(i):
    excerpts = pd.read_excel('../data/Sample_Paragraphs.xlsx', 'Sheet1')
    text = excerpts.loc[i].Paragraph
    text_title = excerpts.loc[i]['Book Title']
    protagonist = excerpts.loc[i].Character
    gender = excerpts.loc[i].Gender
    if gender.lower() == 'female':
        is_female = True
    else:
        is_female = False

    gendered_pronouns = None
    if is_female:
        gendered_pronouns = FEMALE_PRONOUNS
    else:
        gendered_pronouns = MALE_PRONOUNS

    return text, text_title, protagonist, gender, is_female, gendered_pronouns