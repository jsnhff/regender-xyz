
class Protagonist:

    # PROTAGONIST properties
    name = None
    is_female = None
    gendered_pronouns = []
    replacement_name = None
    # OTHER CHARACTER properties
    other_character_replacement_name = None # use when regendering Mrs. Bennet makes her into Mr. Bennet who is already in the book
    # BOOK properties
    text_id = None

    def __init__(self, name, is_female, gendered_pronouns, replacement_name, other_character_replacement_name, text_id):
        self.name = name
        self.is_female = is_female
        self.gendered_pronouns = gendered_pronouns
        self.replacement_name = replacement_name
        self.other_character_replacement_name = other_character_replacement_name
        self.text_id = text_id

    # gets the name of the protagonist
    def get_name(self):
        return self.name

    # sets the name of the protagonist
    def set_name(self, name):
        self.name = name

    # gets the gender of the protagonist; TRUE is female, FALSE if male
    def get_is_female(self):
        return self.is_female

    # sets the gender of the protagonist; TRUE is female, FALSE if male
    def set_is_female(self, is_female):
        self.is_female = is_female

    # gets the list of all English pronouns matching the protagonist's gender
    def get_gendered_pronouns(self):
        return self.gendered_pronouns

    # sets the list of all English pronouns matching the protagonist's gender
    def set_gendered_pronouns(self, gendered_pronouns):
        self.gendered_pronouns = gendered_pronouns

    # gets the replacement name of the protagonist (when regendered)
    def get_replacement_name(self):
        return self.replacement_name

    # sets the replacement name of the protagonist (when regendered)
    def set_replacement_name(self, replacement_name):
        self.replacement_name = replacement_name

    # gets the text_id name of the protagonist - e.g. the unique identifier in config.ini of each book
    def get_text_id(self):
        return self.text_id

    # sets the text_id name of the protagonist - e.g. the unique identifier in config.ini of each book
    def set_text_id(self, text_id):
        self.text_id = text_id

    # gets the replacement name of an existing character in the book, whose name clashes with the protagonist's replacement name
    def get_other_character_replacement_name(self):
        return self.other_character_replacement_name

    # sets the replacement name of an existing character in the book, whose name clashes with the protagonist's replacement name
    def set_other_character_replacement_name(self, other_character_replacement_name):
        self.other_character_replacement_name = other_character_replacement_name