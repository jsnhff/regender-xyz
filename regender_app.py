# Multi-Agent Editor - Regendering Characters
# Enhance the script to use OpenAI's GPT API for nuanced gender changes.

import openai
import re
import os  # Importing os to access environment variables (like the API key)

# Initial setup for OpenAI API - Replace 'YOUR_API_KEY' with your actual OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_gpt_response(prompt, model="gpt-3.5-turbo", temperature=0.7):
    """
    Function to interact with OpenAI's GPT-3.5 API using the chat endpoint.
    """
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
        return None

def detect_roles_gpt(input_text):
    """
    Function to use GPT-3.5 to identify roles, genders, and character details in the input text.
    """
    # Create a prompt to instruct GPT to detect character roles and genders.
    prompt = f"Identify all the characters, their roles, and their genders in the following text:\n\n{input_text}\n\nProvide the results in a structured format like: Character - Role - Gender."
    
    # Get the response from GPT-3.5
    return get_gpt_response(prompt)

def regender_text_gpt(input_text, target_gender="female"):
    """
    Function to use GPT-3.5 for regendering the input text.
    """
    # Detect roles and characters in the text (for better control and understanding of the changes)
    roles_info = detect_roles_gpt(input_text)
    if roles_info:
        print("Detected Roles and Genders:")
        print(roles_info)  # Print detected roles and genders to help understand the context

        # Allow the user to confirm or adjust the genders of characters
        roles = roles_info.splitlines()
        confirmed_roles = []
        for role in roles:
            character, role_desc, gender = role.split(" - ")
            print(f"Character: {character}, Role: {role_desc}, Current Gender: {gender}")
            new_gender = input(f"Enter new gender for {character} (leave blank to keep '{gender}'): ")
            if new_gender:
                confirmed_roles.append(f"{character} - {role_desc} - {new_gender}")
            else:
                confirmed_roles.append(role)
        
        print("\nConfirmed Roles and Genders:")
        for confirmed_role in confirmed_roles:
            print(confirmed_role)
    
    # Create a prompt to instruct GPT on how to change the gender of the text.
    if target_gender == "female":
        prompt = f"Rewrite the following text, changing all male characters to female, including roles, titles, and pronouns:\n\n{input_text}"
    elif target_gender == "male":
        prompt = f"Rewrite the following text, changing all female characters to male, including roles, titles, and pronouns:\n\n{input_text}"
    else:
        raise ValueError("Target gender must be 'female' or 'male'")
    
    # Get the response from GPT-3.5
    return get_gpt_response(prompt)

if __name__ == "__main__":
    # Sample story
    text = "Amidst the darkened village, Prince Leo carried a lantern, its soft glow guiding his steps. Shadows loomed, but he moved on, unafraid. As a brother and a son, he felt responsible. At the ancient oak, he placed the lantern down. Its light spread, revealing a hidden path. Leo smiled, knowing he’d found the way home."
    
    # Detect roles in the text before regendering
    detect_roles_gpt(text)
    
    # Regender the text to female using GPT
    target_gender = input("Enter the target gender (female/male): ").strip().lower()
    if target_gender not in ["female", "male"]:
        print("Invalid gender. Please enter 'female' or 'male'.")
    else:
        regendered_text = regender_text_gpt(text, target_gender=target_gender)
        if regendered_text:
            print("Regendered Text:")
            print(regendered_text)
    # if regendered_text:
    #     print("Regendered Text:")
    #     print(regendered_text)
