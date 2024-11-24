# Multi-Agent Editor - Regendering Characters
# Enhance the script to use OpenAI's GPT API for nuanced gender changes.
# Note: Current implementation of change highlighting can sometimes tag partial word changes (e.g., 'ss' when changing 'Prince' to 'Princess'). Consider improving the logic for word-level differentiation in future updates.

import openai
import re
import os  # Importing os to access environment variables (like the API key)
import datetime  # To timestamp the log entries
import json  # To cache roles for reuse
import time  # To implement retry delays
import difflib  # To highlight changes between original and regendered text

# Initial setup for OpenAI API - Replace 'YOUR_API_KEY' with your actual OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_gpt_response(prompt, model="gpt-3.5-turbo", temperature=0.7, retries=3, delay=5):
    """
    Function to interact with OpenAI's GPT-3.5 API using the chat endpoint.
    Includes retry mechanism for handling API errors.
    """
    attempt = 0
    while attempt < retries:
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=temperature
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            print(f"Error: {e}")
            attempt += 1
            if attempt < retries:
                print(f"Retrying in {delay} seconds... (Attempt {attempt + 1} of {retries})")
                time.sleep(delay)
            else:
                print("Maximum retries reached. Please check your connection or API key and try again.")
                return None

def detect_roles_gpt(input_text):
    """
    Function to use GPT-3.5 to identify roles, genders, and character details in the input text.
    """
    # Create a prompt to instruct GPT to detect character roles and genders.
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender."
    
    # Get the response from GPT-3.5
    return get_gpt_response(prompt)

def log_output(log_file_path, original_text, roles_info, confirmed_roles, regendered_text, highlighted_text=None):
    """
    Function to log the entire process to a log file.
    """
    with open(log_file_path, 'w') as log_file:
        log_file.write("Log File for Multi-Agent Editor\n")
        log_file.write(f"File Name: {log_file_path}\n")
        log_file.write(f"Script Name: {os.path.basename(__file__)}\n")
        log_file.write(f"Timestamp: {datetime.datetime.now()}\n\n")
        
        # Write original text
        log_file.write("Original Story:\n")
        log_file.write(f"{original_text}\n\n")
        
        # Write detected roles and genders
        log_file.write("Detected Roles and Genders:\n")
        log_file.write(f"{roles_info}\n\n")
        
        # Write confirmed roles and changes made by the user
        log_file.write("Confirmed Roles and Genders after User Input:\n")
        for confirmed_role in confirmed_roles:
            log_file.write(f"{confirmed_role}\n")
        log_file.write("\n")
        
        # Write the final regendered text
        log_file.write("Final Regendered Output:\n")
        log_file.write(f"{regendered_text}\n\n")
        
        # Write the highlighted text if provided
        if highlighted_text:
            log_file.write("Highlighted Changes:\n")
            log_file.write(f"{highlighted_text}\n")

def load_cached_roles(cache_file="roles_cache.json"):
    """
    Load cached roles from a JSON file.
    """
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            return json.load(file)
    return {}

def save_cached_roles(roles, cache_file="roles_cache.json"):
    """
    Save confirmed roles to a JSON file.
    """
    with open(cache_file, 'w') as file:
        json.dump(roles, file, indent=4)

def confirm_roles(roles_info, cached_roles):
    """
    Function to allow user to confirm or adjust the detected roles and genders.
    """
    confirmed_roles = []
    roles = roles_info.splitlines()
    for role in roles:
        character, role_desc, gender = role.split(" - ")
        # Check if the character is already in the cached roles
        if character in cached_roles:
            cached_role = cached_roles[character]
            print(f"Character: {character}, Cached Role: {cached_role['role']}, Cached Gender: {cached_role['gender']}")
            use_cached = input(f"Use cached role and gender for {character}? (y/n): ").strip().lower()
            if use_cached == 'y':
                confirmed_roles.append(f"{character} - {cached_role['role']} - {cached_role['gender']}")
                continue
        
        # If not using cached role, confirm or adjust
        print(f"Character: {character}, Role: {role_desc}, Current Gender: {gender}")
        new_gender = input(f"Enter new gender for {character} (leave blank to keep '{gender}'): ")
        if new_gender:
            confirmed_roles.append(f"{character} - {role_desc} - {new_gender}")
            cached_roles[character] = {"role": role_desc, "gender": new_gender}
        else:
            confirmed_roles.append(role)
            cached_roles[character] = {"role": role_desc, "gender": gender}
    return confirmed_roles

def regender_text_gpt(input_text, confirmed_roles, target_gender="female"):
    """
    Function to use GPT-3.5 for regendering the input text.
    """
    # Create a prompt to instruct GPT on how to change the gender of the text, taking confirmed roles into account.
    role_adjustments = "\n".join(confirmed_roles)
    prompt = f"Rewrite the following text, changing characters based on the given adjustments. Adjust roles, titles, and pronouns accordingly:\n\nRoles Adjustments:\n{role_adjustments}\n\nText:\n{input_text}"
    
    # Get the response from GPT-3.5
    return get_gpt_response(prompt)

def highlight_changes(original_text, regendered_text):
    """
    Highlight changes between the original and regendered text using XML-like tags.
    Note: Current implementation may tag partial word changes (e.g., 'ss' when changing 'Prince' to 'Princess').
    Future improvement could focus on better word-level differentiation.
    """
    matcher = difflib.SequenceMatcher(None, original_text, regendered_text)
    highlighted_text = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace' or tag == 'insert':
            highlighted_text.append(f"<changed>{regendered_text[j1:j2]}</changed>")
        elif tag == 'equal':
            highlighted_text.append(regendered_text[j1:j2])
    return ''.join(highlighted_text)

def create_highlighted_xml_log(xml_log_file_path, highlighted_text):
    """
    Create an XML log file with highlighted changes for use in InDesign.
    """
    with open(xml_log_file_path, 'w') as xml_file:
        xml_file.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        xml_file.write("<document>\n")
        xml_file.write(f"  <content>{highlighted_text}</content>\n")
        xml_file.write("</document>\n")

if __name__ == "__main__":
    # Sample story
    text = "Amidst the darkened village, Prince Leo and King Harry carried a lantern, its soft glow guiding their steps. Shadows loomed, but they moved on, unafraid. Leo was Harry's son, and he felt responsible for his father's life. At the ancient oak, Leo placed the lantern down by Harry's feet. Its light spread, revealing a hidden path. Leo smiled, knowing he’d found the way home."
    
    # Create a unique log file name using the timestamp and program name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    log_file_name = f"{script_name}_regender_log_{timestamp}.txt"
    log_file_dir = "logs"
    log_file_path = os.path.join(log_file_dir, log_file_name)
    highlighted_log_file_path = os.path.join(log_file_dir, f"{script_name}_highlighted_log_{timestamp}.txt")
    highlighted_xml_log_file_path = os.path.join(log_file_dir, f"{script_name}_highlighted_log_{timestamp}.xml")
    
    # Ensure the log directory exists
    if not os.path.exists(log_file_dir):
        os.makedirs(log_file_dir)
    
    # Load cached roles
    cached_roles = load_cached_roles()
    
    # Detect roles in the text before regendering
    roles_info = detect_roles_gpt(text)
    if roles_info:
        print("Detected Roles and Genders:")
        print(roles_info)
        
        # Confirm roles and genders with the user, using cached roles where applicable
        confirmed_roles = confirm_roles(roles_info, cached_roles)
        
        # Ask if the user wants to save the confirmed roles to the cache as the default for future runs
        save_to_cache = input("Would you like to save these confirmed roles as the default for future runs? (y/n): ").strip().lower()
        if save_to_cache == 'y':
            save_cached_roles(cached_roles)
        
        # Regender the text using GPT with confirmed roles
        regendered_text = regender_text_gpt(text, confirmed_roles, target_gender="female")
        
        # Highlight changes between original and regendered text
        highlighted_text = highlight_changes(text, regendered_text) if regendered_text else None
        
        # Log the output to files
        log_output(log_file_path, text, roles_info, confirmed_roles, regendered_text)
        if highlighted_text:
            log_output(highlighted_log_file_path, text, roles_info, confirmed_roles, regendered_text, highlighted_text)
            create_highlighted_xml_log(highlighted_xml_log_file_path, highlighted_text)
        
        if regendered_text:
            print("Regendered Text:")
            print(regendered_text)

        if highlighted_text:
            print("\nHighlighted Changes:")
            print(highlighted_text)
