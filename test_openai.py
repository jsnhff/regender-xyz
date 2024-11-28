import os
from openai import OpenAI

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Create a chat completion
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # Replace with "gpt-4" if you have access
    messages=[
        {"role": "user", "content": "Say something cool!"}
    ]
)

# Print the response content
print(response.choices[0].message.content)

