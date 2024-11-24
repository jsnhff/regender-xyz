import openai  # Importing OpenAI API to interact with GPT models
import threading  # Importing threading to allow multiple agents to edit concurrently
import os  # Importing os to access environment variables (like the API key)
import re  # Importing re to use regular expressions for pattern matching in text

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

class MultiAgentEditor:
    def __init__(self):
        self.content = "Amidst the darkened village, Prince Leo carried a lantern, its soft glow guiding his steps. Shadows loomed, but he moved on, unafraid. As a brother and a son, he felt responsible. At the ancient oak, he placed the lantern down. Its light spread, revealing a hidden path. Leo smiled, knowing he’d found the way home."
        self.lock = threading.Lock()
        
        # BEGIN NEW CODE FOR LOGGING
        self.log_file = "edit_log.txt"  # This file will be used to store all logs of edits
        self.character_name_map = {}  # Stores old to new character name mappings dynamically
        # END NEW CODE FOR LOGGING

    def edit_content(self, agent_name, prompt, temperature=0.7, max_tokens=150):
        with self.lock:
            print(f"{agent_name} is editing the content...")
            full_prompt = f"\n======\nCurrent content:\n{self.content}\n\n{prompt}"
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
                self.content += "\n" + edited_content
                
                # BEGIN NEW CODE FOR LOGGING EDITS
                self.log_edit(agent_name, prompt, edited_content)  # Logging the edit
                # END NEW CODE FOR LOGGING EDITS
                
                # BEGIN NEW CODE FOR CONSISTENCY CHECK
                if not self.check_consistency(agent_name, edited_content, prompt):
                    print(f"\n+++++\n{agent_name}: Consistency check failed. Please review the edit.")
                # END NEW CODE FOR CONSISTENCY CHECK
                
                print(f"{agent_name} finished editing. Current content:\n{self.content}\n")
            except Exception as e:
                print(f"\n******\nError during {agent_name}'s editing: {e}")

    # BEGIN NEW METHOD FOR LOGGING EDITS
    def log_edit(self, agent_name, prompt, edited_content):
        """Logs each edit to a file for future reference."""
        with open(self.log_file, 'a') as log:
            log.write(f"Agent: {agent_name}\nPrompt: {prompt}\nEdit: {edited_content}\n")
            log.write("="*40 + "\n")
    # END NEW METHOD FOR LOGGING EDITS

    # BEGIN UPDATED METHOD FOR CONSISTENCY CHECK
    def check_consistency(self, agent_name, edited_content, prompt):
        """Checks for broader consistency in the edited content."""
        issues = []
        
        # Check for conflicting pronouns (e.g., he/she, his/her)
        if re.search(r'\bhe\b.*\bshe\b|\bshe\b.*\bhe\b', edited_content, re.IGNORECASE):
            issues.append("Conflicting pronouns detected.")
        if re.search(r'\bhis\b.*\bher\b|\bher\b.*\bhis\b', edited_content, re.IGNORECASE):
            issues.append("Conflicting possessive pronouns detected.")
        
        # BEGIN NEW CODE FOR DYNAMIC NAME CONSISTENCY CHECK
        # Ensure character names are consistently changed dynamically
        for old_name, new_name in self.character_name_map.items():
            if re.search(fr'\b{old_name}\b', edited_content) and re.search(fr'\b{new_name}\b', edited_content):
                issues.append(f"Inconsistent use of character names: {old_name} and {new_name} found together.")
        
        # Update character name mapping if prompt indicates a name change
        name_change_match = re.search(r'Change the name from (\w+) to (\w+)', prompt)
        if name_change_match:
            old_name, new_name = name_change_match.groups()
            self.character_name_map[old_name] = new_name
        # END NEW CODE FOR DYNAMIC NAME CONSISTENCY CHECK
        
        # BEGIN UPDATED CODE FOR LOGICAL INCONSISTENCIES
        # Generalize logical inconsistency checks based on gender-specific traits
        logical_inconsistencies = [
            (r'\b(beard|mustache|stubble)\b', "she|her"),
            (r'\b(pregnant|wearing a dress)\b', "he|his"),
            (r'\b(queen)\b', "he|his"),
            (r'\b(king)\b', "she|her")
        ]
        for trait, conflicting_pronoun in logical_inconsistencies:
            if re.search(trait, edited_content, re.IGNORECASE) and re.search(conflicting_pronoun, edited_content, re.IGNORECASE):
                issues.append(f"Logical inconsistency detected: Trait '{trait}' conflicts with pronoun '{conflicting_pronoun}'.")
        # END UPDATED CODE FOR LOGICAL INCONSISTENCIES

        # BEGIN NEW CODE FOR RELATIONSHIP CONSISTENCY
        # Ensure family relationships change according to gender (e.g., 'father' to 'mother', 'brother' to 'sister')
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
        # END NEW CODE FOR RELATIONSHIP CONSISTENCY
        
        if issues:
            # Log the issues found
            with open(self.log_file, 'a') as log:
                log.write(f"Agent: {agent_name} - Consistency Issues Found:\n")
                for issue in issues:
                    log.write(f"- {issue}\n")
                log.write("="*40 + "\n")
            return False
        return True
    # END UPDATED METHOD FOR CONSISTENCY CHECK

# Main function to demonstrate multi-agent editing flow
def main():
    editor = MultiAgentEditor()

    agents = [
        ("Agent 1", "Change the gender of the male character and all related pronouns, articles, titles, and clothing to female."),
        ("Agent 2", "Check the changes"),
        ("Agent 3", "Review the new document and make sure the character is female and not male."),
    ]

    threads = []
    for agent_name, prompt in agents:
        thread = threading.Thread(target=editor.edit_content, args=(agent_name, prompt))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\nFinal Content:\n", editor.content)

if __name__ == "__main__":
    main()