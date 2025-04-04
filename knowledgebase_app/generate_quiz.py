from openai import OpenAI
from dotenv import load_dotenv
import os
import json

def generate_quiz_from_openai(quiz_topic:str):
    load_dotenv()
    
    CONTENT_PROMPT = f"""
    Hello! You are a Tutor. You are helping a student who wants to improve their understanding in various computer topics.
    Generate 10 questions about "{quiz_topic}" in JSON format as follows: """ + """
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

def adjust_difficulty(current_difficulty, was_correct):
    """Adjust difficulty based on whether the previous answer was correct"""
    difficulty_levels = ['Easy', 'Medium', 'Hard', 'Expert']
    
    # Find current index
    try:
        current_index = difficulty_levels.index(current_difficulty)
    except ValueError:
        # Default to Medium if invalid difficulty provided
        current_index = 1
    
    if was_correct:
        # Move up one difficulty level if correct (max at Expert)
        new_index = min(current_index + 1, len(difficulty_levels) - 1)
    else:
        # Move down one difficulty level if incorrect (min at Easy)
        new_index = max(current_index - 1, 0)
    
    return difficulty_levels[new_index]

def generate_initial_questions(quiz_topic, count=5):
    """Generate initial quiz questions at medium difficulty"""
    # For first-time quiz takers, generate questions at medium difficulty
    questions = []
    
    # Use OpenAI to generate questions with difficulty parameter
    openai_questions = generate_quiz_from_openai_with_difficulty(quiz_topic, 'Medium', count)
    
    # Add difficulty metadata to each question
    for i, q in enumerate(openai_questions):
        q['difficulty'] = 'Medium'
        q['question_id'] = f"q_{i}_initial"
        questions.append(q)
    
    return questions

def generate_adaptive_questions(quiz_topic, questions_with_difficulty):
    """Generate new questions based on previous performance"""
    questions = []
    
    # Group questions by difficulty to minimize API calls
    difficulty_groups = {}
    for q in questions_with_difficulty:
        difficulty = q['next_difficulty']
        if difficulty not in difficulty_groups:
            difficulty_groups[difficulty] = 0
        difficulty_groups[difficulty] += 1
    
    # Generate questions for each difficulty level
    question_id_counter = 0
    for difficulty, count in difficulty_groups.items():
        # Generate questions at this difficulty level
        openai_questions = generate_quiz_from_openai_with_difficulty(quiz_topic, difficulty, count)
        
        # Add metadata
        for q in openai_questions:
            q['difficulty'] = difficulty
            q['question_id'] = f"q_{question_id_counter}_adaptive"
            question_id_counter += 1
            questions.append(q)
    
    return questions

def generate_quiz_from_openai_with_difficulty(quiz_topic, difficulty, count=5):
    """Enhanced version of generate_quiz_from_openai that includes difficulty"""
    load_dotenv()
    
    difficulty_descriptions = {
        'Easy': "basic recall and simple application questions suitable for beginners",
        'Medium': "moderate application and analysis questions requiring good understanding",
        'Hard': "challenging questions requiring deep understanding and complex problem-solving",
        'Expert': "very challenging questions requiring mastery and advanced problem-solving skills"
    }
    
    difficulty_desc = difficulty_descriptions.get(difficulty, difficulty_descriptions['Medium'])
    
    CONTENT_PROMPT = f"""
    Hello! You are a Tutor. You are helping a student who wants to improve their understanding in various topics.
    Generate {count} {difficulty.lower()} difficulty questions about "{quiz_topic}" in JSON format. 
    
    These should be {difficulty_desc}.
    
    Format as follows: """ + """
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
    
    try:
        questions = json.loads(chat_completion.choices[0].message.content)
        return questions
    except Exception as e:
        print(f"Error parsing OpenAI response: {str(e)}")
        # Return empty list in case of error
        return []
