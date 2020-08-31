# imports
import pandas as pd
import spacy
import neuralcoref

# load needed language resources
nlp = spacy.load('en_core_web_sm')
neuralcoref.add_to_pipe(nlp)

