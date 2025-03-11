from openai import OpenAI
from dotenv import load_dotenv
import os
import json

def generate_quiz_from_openai(quiz_topic:str):
    load_dotenv()
    
    CONTENT_PROMPT = f"""
    Hello! You are a Tutor. You are helping a student who wants to improve their understanding in various topics.
    Generate 5 questions about "{quiz_topic}" in JSON format as follows: """ + """
    [
        {
            "question":"question text goes here",
            "choices": ["choice 1", "choice 2", "choice 3", "choice 4"],
            "correct_answer":<correct answer index>
        }
    ]
    
    Please only return the JSON object with the questions and choices. Do not include this prompt or any other text.
    Also, please don't include the ```json``` tag in the response. Thank you!
    """
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": CONTENT_PROMPT,
            }
        ],
        model="gpt-4o",
    )

    print(chat_completion.choices[0].message.content)
    
    # TODO: implement error handling
    questions = json.loads(chat_completion.choices[0].message.content)
    return questions
