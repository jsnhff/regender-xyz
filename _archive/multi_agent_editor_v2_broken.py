import openai  # Importing OpenAI API to interact with GPT models
import threading  # Importing threading to allow multiple agents to edit concurrently
import os  # Importing os to access environment variables (like the API key)
import re  # Importing re to use regular expressions for pattern matching in text

# Set your OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

class MultiAgentEditor:
    def __init__(self):
        self.content = ""
        self.lock = threading.Lock()
        
        # BEGIN NEW CODE FOR LOGGING AND PRE-EDIT ANALYSIS
        self.log_file = "edit_log.txt"  # This file will be used to store all logs of edits
        self.character_name_map = {}  # Stores old to new character name mappings dynamically
        self.character_tags = {}  # Stores character and role tags for consistency
        self.edit_history = []  # Stores changes made to overlapping content to avoid redundancy
        # END NEW CODE FOR LOGGING AND PRE-EDIT ANALYSIS

    def pre_edit_analysis(self, content):
        """Analyzes the content and tags key elements like character names and roles for consistency."""
        # This is a simplified analysis to identify character names and roles.
        # In practice, this could involve more advanced NLP techniques.
        character_names = re.findall(r'\b[A-Z][a-z]+\b', content)
        for character in character_names:
            # Tag the character name (in a real scenario, identify unique names intelligently)
            self.character_tags[character] = f"[Character: {character}]"
        
        # Example: Add more specific role tagging (e.g., father, king, etc.)
        roles = ["father", "mother", "king", "queen", "brother", "sister", "son", "daughter", "caregiver"]
        for role in roles:
            if re.search(fr'\b{role}\b', content, re.IGNORECASE):
                self.character_tags[role] = f"[Role: {role}]"

        # Replace identified tags in the content
        for key, tag in self.character_tags.items():
            content = re.sub(fr'\b{key}\b', tag, content)
        
        return content

    def chunk_content(self, content, chunk_size=2000, overlap_size=200):
        """Splits the content into larger logical sections, then into smaller chunks to fit API limits."""
        # Split content into parts based on chapters or logical sections
        parts = re.split(r'\nChapter [0-9]+|\nCHAPTER [0-9]+', content)
        chunks = []

        for part in parts:
            if not part.strip():
                continue
            words = part.split()
            current_chunk = []
            current_length = 0

            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                # Add overlap if this isn't the last chunk of the part
                if i + chunk_size < len(words):
                    overlap = words[i + chunk_size:i + chunk_size + overlap_size]
                    chunk.extend(overlap)
                chunks.append(" ".join(chunk))

        return chunks

    def edit_content(self, agent_name, prompt, temperature=0.7, max_tokens=300):
        with self.lock:
            print(f"{agent_name} is editing the content...")
            # Run pre-edit analysis first
            self.content = self.pre_edit_analysis(self.content)
            chunks = self.chunk_content(self.content)
            new_content = ""
            previous_chunk = ""  # Store the previous chunk to handle overlap more effectively
            
            for chunk in chunks:
                # Avoid redundant edits by making sure that overlapping parts are not edited twice
                overlap_handled_chunk = self.handle_overlap(previous_chunk, chunk)

                full_prompt = f"Current content:\n{overlap_handled_chunk}\n\n{prompt}"
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
                    edited_chunk = response.choices[0].message["content"].strip()
                    new_content += "\n" + edited_chunk
                    self.edit_history.append((chunk, edited_chunk))  # Log edits made to avoid redundancy
                except Exception as e:
                    print(f"Error during {agent_name}'s editing: {e}")
                    new_content += "\n" + chunk  # In case of an error, keep the original chunk

                # Update previous chunk
                previous_chunk = chunk

            self.content = new_content
            
            # BEGIN NEW CODE FOR LOGGING EDITS
            self.log_edit(agent_name, prompt, new_content)  # Logging the edit
            # END NEW CODE FOR LOGGING EDITS
            
            # BEGIN NEW CODE FOR CONSISTENCY CHECK
            if not self.check_consistency(agent_name, new_content, prompt):
                print(f"{agent_name}: Consistency check failed. Please review the edit.")
            # END NEW CODE FOR CONSISTENCY CHECK
            
            print(f"{agent_name} finished editing. Current content:\n{self.content}\n")

    def handle_overlap(self, previous_chunk, current_chunk):
        """Avoids redundant edits by comparing overlapping parts and skipping edits already performed."""
        if not previous_chunk:
            return current_chunk  # No overlap for the first chunk

        overlap_start = len(previous_chunk) - len(current_chunk)
        if overlap_start > 0:
            # Check if overlap was already edited and skip redundant edits
            overlap_section = current_chunk[:overlap_start]
            for old_chunk, edited_chunk in self.edit_history:
                if overlap_section in old_chunk:
                    return edited_chunk + current_chunk[overlap_start:]
        return current_chunk

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

    # BEGIN NEW METHOD TO PRINT CHARACTER MAP AND EDIT HISTORY
    def print_summary(self):
        """Prints the character map and change log summary."""
        print("\nCharacter Name Mapping:")
        for old_name, new_name in self.character_name_map.items():
            print(f"{old_name} -> {new_name}")
        
        print("\nEdit History:")
        for original, edited in self.edit_history:
            print(f"Original: {original}\nEdited: {edited}\n{'='*40}")
    # END NEW METHOD TO PRINT CHARACTER MAP AND EDIT HISTORY

# Main function to demonstrate multi-agent editing flow
def main():
    editor = MultiAgentEditor()
    editor.content = "Once upon a time, there was a young prince named Holden. He loved to care for his family and support his mother, the queen."
    print("Initial content:", editor.content) # test content load

    agents = [
        ("Agent 1", "Write a short story about a man that is 500 words long, includes male titles like prince or king, male clothing, and references to family relationships like father and brother."),
        ("Agent 2", "Change the gender of the male character and all related pronouns, articles, titles, and clothing to female."),
        ("Agent 3", "Check the changes"),
        ("Agent 4", "Review the new document and make sure the character is female and not male."),
    ]

    threads = []
    for agent_name, prompt in agents:
        thread = threading.Thread(target=editor.edit_content, args=(agent_name, prompt))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\nFinal Content:\n", editor.content)
    # BEGIN NEW CODE TO PRINT SUMMARY
    editor.print_summary()  # Print character name mapping and edit history summary
    # END NEW CODE TO PRINT SUMMARY

if __name__ == "__main__":
    main()