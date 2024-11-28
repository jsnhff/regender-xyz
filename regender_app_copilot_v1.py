import os
import time
import difflib
from openai import OpenAI

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def check_openai_api_key():
    try:
        # Make a simple request to the OpenAI API to check if the API key is valid
        client.models.list()
        print("OpenAI API key is valid.")
    except Exception as e:
        print(f"Error: {e}")
        print("OpenAI API key is invalid or there is an issue with the connection.")

# Call the function to check the API key
check_openai_api_key()

def get_gpt_response(prompt, model="gpt-3.5-turbo", temperature=0.7, retries=3, delay=5):
    """
    Function to interact with OpenAI's GPT-3.5 API using the chat endpoint.
    Includes retry mechanism for handling API errors.
    """
    attempt = 0
    while attempt < retries:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error: {e}")
            attempt += 1
            time.sleep(delay)
    return None

def detect_roles_gpt(input_text):
    """
    Function to use GPT-3.5 to identify roles, genders, and character details in the input text.
    """
    # Create a prompt to instruct GPT to detect character roles and genders.
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender."
    
    # Get the response from GPT-3.5
    response = get_gpt_response(prompt)
    return response

def regender_text_gpt(input_text, confirmed_roles, target_gender="female"):
    """
    Function to use GPT-3.5 for regendering the input text.
    """
    # Create a prompt to instruct GPT to regender the text
    prompt = f"Regender the following text to {target_gender}:\n\n{input_text}\n\nRoles and genders:\n{confirmed_roles}"
    
    # Get the response from GPT-3.5
    response = get_gpt_response(prompt)
    return response

def highlight_changes(original_text, regendered_text):
    """
    Function to highlight changes between original and regendered text.
    """
    return '\n'.join(difflib.unified_diff(original_text.splitlines(), regendered_text.splitlines()))

def log_output(file_path, *args):
    """
    Function to log the output to a file.
    """
    with open(file_path, 'w') as file:
        for arg in args:
            file.write(str(arg) + "\n")

def create_highlighted_xml_log(file_path, highlighted_text):
    """
    Function to create an XML log of highlighted changes.
    """
    # Placeholder for actual implementation
    pass

def load_input_text(file_path):
    """
    Function to load input text from a file.
    """
    with open(file_path, 'r') as file:
        return file.read()

def confirm_roles(roles_info):
    """
    Function to confirm roles and genders with the user.
    """
    # Placeholder for actual implementation
    return roles_info

def main():
    # Load the input text from a file or user input
    input_text = load_input_text("input.txt")

    # Detect roles and genders in the input text
    roles_info = detect_roles_gpt(input_text)
    if roles_info:
        print("Detected Roles and Genders:")
        print(roles_info)

        # Confirm roles and genders with the user
        confirmed_roles = confirm_roles(roles_info)

        # Regender the text using GPT with confirmed roles
        regendered_text = regender_text_gpt(input_text, confirmed_roles, target_gender="female")

        # Highlight changes between original and regendered text
        highlighted_text = highlight_changes(input_text, regendered_text) if regendered_text else None

        # Log the output to files
        log_output("log.txt", input_text, roles_info, confirmed_roles, regendered_text)
        if highlighted_text:
            log_output("highlighted_log.txt", input_text, roles_info, confirmed_roles, regendered_text, highlighted_text)
            create_highlighted_xml_log("highlighted_log.xml", highlighted_text)

if __name__ == "__main__":
    main()