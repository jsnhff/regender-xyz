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

def google_login():
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


# if i = 8, we load Pride and Prejudice excerpt
def load_exceprt_data(text_id):

    # get the file with the text from config.ini
    TEXT_FILE = root_dir + os.sep + config.get(text_id, 'TEXT_FILE')
    TEXT_FILE_SHEET = config.get(text_id, 'TEXT_FILE_SHEET')

    if TEXT_FILE_SHEET != 'None':
        SHEET_LINE = int(config.get(text_id, 'SHEET_LINE')) # as we originally read it as a STR from config.ini
        excerpts = pd.read_excel(TEXT_FILE, TEXT_FILE_SHEET)
    else:
        # creds = google_login()
        # gdd.download_file_from_google_drive(file_id='1UQkkYWjSUmilX6loSQkpwxNHPr4XZ6l2',
        #                                     dest_path=root_dir + os.sep + 'data/' +  text_id + '.docx',
        #                                     credentials=creds)
        # excerpts = read_doc()

        url = ''
        gdown.download(url, root_dir + 'donwload.txt', quiet=False)

    text = excerpts.loc[SHEET_LINE].Paragraph
    protagonist = excerpts.loc[SHEET_LINE].Character
    gender = excerpts.loc[SHEET_LINE].Gender

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