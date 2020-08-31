### Spacy: co-reference resolution

**Links**

1. [NeuralCoref Universe](https://spacy.io/universe/project/neuralcoref) & Documentation in the for of [README.md](https://github.com/huggingface/neuralcoref)
2. [NeuralCoref Visualizer](https://spacy.io/universe/project/neuralcoref-vizualizer)
3. [NeuralCoref Source Code on Github](https://github.com/huggingface/neuralcoref)
4. [blog post: Coreference resolution using Spacy](https://www.rangakrish.com/index.php/2019/02/03/coreference-resolution-using-spacy/)


### Installation & Dependencies

1. Create a virtual environment on which to work on (in terminal) & install all needed packages

```sh
python3 -m venv nlp # creates the virtual enviornment
pip3 install -r requrements.txt # install app Python dependencies (needed packages)
```

a. every time you work on the project, activate this virtual environment

```sh
souce nlp/bin/activate
```

2. Install NeuralCoref from core & the correct associated version of Spacy with it

```sh
pip uninstall neuralcoref
git clone https://github.com/huggingface/neuralcoref.git
cd neuralcoref
pip install -r requirements.txt
pip install -e .
pip uninstall spacy
pip install spacy
python -m spacy download en
```

test it quickly in Python to ensure that it works as expected:

```py
import spacy
nlp = spacy.load('en')
import neuralcoref      ## ignore RuntimeWarning(s)
neuralcoref.add_to_pipe(nlp)
doc = nlp(u'My sister has a dog. She loves him.')
doc._.has_coref         ## True
doc._.coref_clusters    ## [My sister: [My sister, She], a dog: [a dog, him]]
doc._.coref_resolved    ## 'My sister has a dog. My sister loves a dog.'
```

Link with installation insturctuons found [here](https://github.com/huggingface/neuralcoref)