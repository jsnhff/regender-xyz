# Regender Books

ToC:
1. [Initial Set-up & Installation](#initial-setup)
2. [How to run](#run)
3. [Approach](#approach)
3. [Analysing a new piece of text](#continuing-work)
4. [Progress - a.k.a What's been analysed so far](#progress)
5. [Project Management](#management)
4. [Libraries Used](#libraries)
5. [Resources and References](#resources-and-references)

---


### Initial Set-up & Installation <a name="initial-setup"></a>

1. Clone the git repo on your local machine by either:
- downloading the `.zip` folder of the repo from [here](https://github.com/estambolieva/regendered-books/archive/master.zip) and decompressing it in a location of your choice on your machine, OR
- opening up the terminal, and using `git`:


Check if you have git installed:

```sh
git --version # check if you have git isntalled
> git version 2.XX.XX # OUTPUT if git is installed.If not, type in
```

Install `git` on **Linux**:

```sh
sudo apt update
sudo apt install git # install git on Linux
```


Install `git` on **Mac**:

```sh
brew install git # install git on Mac
```

Finally clone the project

```sh

git clone https://github.com/estambolieva/regendered-books.git
```


2. Create a virtual environment on which to work on (in terminal) & install all needed packages

In the root folder of the project - create a virtual environment to use when working on the projects - on which we install all needed packages

```sh
python3 -m venv nlp # creates the virtual enviornment
```

a. every time you work on the project, activate this virtual environment as the first step after opening the terminal. 

```sh
souce nlp/bin/activate
```

Before I activate the virtual environment, my terminal window prompt looks something like this: `katia@katias-laptop`, and like this - `(nlp)katia@katias-laptop` - after I activate the environment. The `(nlp)` shows me  that the environment has been activated :+1:.  

**Only once**, install all required pythong packages needed by executing

```sh
pip3 install -r requrements.txt # install app Python dependencies (needed packages)
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

test it quickly (if you'd like) in a Python console to ensure that it works as expected:

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


using Trello as a Task manager, and Google Docs for human-understandable documentation.

---

## Resources and References <a name="resources-and-references"></a>

1. [NeuralCoref Universe](https://spacy.io/universe/project/neuralcoref) & Documentation in the for of [README.md](https://github.com/huggingface/neuralcoref)
2. [NeuralCoref Visualizer](https://spacy.io/universe/project/neuralcoref-vizualizer)
3. [NeuralCoref Source Code on Github](https://github.com/huggingface/neuralcoref)
4. [blog post: Coreference resolution using Spacy](https://www.rangakrish.com/index.php/2019/02/03/coreference-resolution-using-spacy/)