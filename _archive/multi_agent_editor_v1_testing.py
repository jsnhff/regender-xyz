import openai
import os
import re
import time

# Set your OpenAI API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it before running the script.")
openai.api_key = api_key

class MultiAgentEditor:
    def __init__(self):
        self.content = "Amidst the darkened village, Prince Leo carried a lantern, its soft glow guiding his steps. Shadows loomed, but he moved on, unafraid. As a brother and a son, he felt responsible. At the ancient oak, he placed the lantern down. Its light spread, revealing a hidden path. Leo smiled, knowing he’d found the way home."
        self.log_file = "edit_log.txt"
        self.character_name_map = {}  # Track character name changes
        self.edit_history = []  # Track edit history
        self.log = open(self.log_file, 'w')  # Open the log file
        self.original_content = self.content  # Store original content for comparison

    def __del__(self):
        if self.log:
            self.log.close()

    def edit_content(self, agent_name, prompt, temperature=0.7, max_tokens=500, retries=3, delay=5):
        print(f"{agent_name} is editing the content...")
        full_prompt = f"{self.content}\n\n{prompt}"
        attempt = 0
        while attempt < retries:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                edited_content = response.choices[0].message["content"].strip()
                print(f"Before Edit ({agent_name}):\n{self.content}\n")
                self.content = edited_content
                print(f"After Edit ({agent_name}):\n{self.content}\n")
                self.log_edit(agent_name, prompt, edited_content)
                if not self.check_consistency(agent_name, edited_content, prompt):
                    print(f"{agent_name}: Consistency check failed. Please review the edit.")
                break
            except Exception as e:
                attempt += 1
                print(f"Error during {agent_name}'s editing (attempt {attempt}): {e}")
                if attempt < retries:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"Failed after {retries} attempts. Skipping this edit.")

    def log_edit(self, agent_name, prompt, edited_content):
        self.log.write(f"Agent: {agent_name}\nPrompt: {prompt}\nEdit: {edited_content}\n")
        self.log.write("="*40 + "\n")

    def check_consistency(self, agent_name, edited_content, prompt):
        issues = []
        if re.search(r'\bhe\b.*\bshe\b|\bshe\b.*\bhe\b', edited_content, re.IGNORECASE):
            issues.append("Conflicting pronouns detected.")
        if re.search(r'\bhis\b.*\bher\b|\bher\b.*\bhis\b', edited_content, re.IGNORECASE):
            issues.append("Conflicting possessive pronouns detected.")
        for old_name, new_name in self.character_name_map.items():
            if re.search(fr'\b{old_name}\b', edited_content) and re.search(fr'\b{new_name}\b', edited_content):
                issues.append(f"Inconsistent use of character names: {old_name} and {new_name} found together.")
        name_change_match = re.search(r'Change the name from (\w+) to (\w+)', prompt)
        if name_change_match:
            old_name, new_name = name_change_match.groups()
            self.character_name_map[old_name] = new_name
        logical_inconsistencies = [
            (r'\b(beard|mustache|stubble)\b', "she|her"),
            (r'\b(pregnant|wearing a dress)\b', "he|his")
        ]
        for trait, conflicting_pronoun in logical_inconsistencies:
            if re.search(trait, edited_content, re.IGNORECASE) and re.search(conflicting_pronoun, edited_content, re.IGNORECASE):
                issues.append(f"Logical inconsistency detected: Trait '{trait}' conflicts with pronoun '{conflicting_pronoun}'.")
        relationship_pairs = [
            ("father", "mother"),
            ("brother", "sister"),
            ("son", "daughter"),
            ("uncle", "aunt"),
            ("king", "queen"),
        ]
        for male_term, female_term in relationship_pairs:
            if re.search(fr'\b{male_term}\b', edited_content) and re.search(fr'\b{female_term}\b', edited_content):
                issues.append(f"Inconsistent use of relationship terms: {male_term} and {female_term} found together.")
        if issues:
            self.log.write(f"Agent: {agent_name} - Consistency Issues Found:\n")
            for issue in issues:
                self.log.write(f"- {issue}\n")
            self.log.write("="*40 + "\n")
            return False
        return True

    def compare_with_original(self):
        print("Comparing original content with edited content...")
        self.log.write("Original Content:\n")
        self.log.write(self.original_content + "\n")
        self.log.write("="*40 + "\n")
        self.log.write("Final Edited Content:\n")
        self.log.write(self.content + "\n")
        self.log.write("="*40 + "\n")
        print("Comparison complete. See log for details.")


def main():
    editor = MultiAgentEditor()
    print("Initial content:", editor.content)
    editor.log.write(f"Initial content:\n{editor.content}\n{'='*40}\n")
    agents = [
        ("Agent 1", "Identify a single character name and log it. Do not change the story text."),
        ("Agent 2", "Change the gender of a single character (e.g., 'Prince' to 'Princess', 'he' to 'she'). Do not make any other changes."),
        ("Agent 3", "Ensure the gender change is consistently applied throughout the text for the character edited by Agent 2."),
        ("Agent 4", "Verify the gender changes do not impact the plot or add any new details. Focus only on the edited character."),
        ("Agent 5", "Output the final version of the story without making any further edits.")
    ]
    for agent_name, prompt in agents:
        editor.edit_content(agent_name, prompt)
    editor.compare_with_original()
    print("\nFinal Revised Version:\n", editor.content)

if __name__ == "__main__":
    main()
