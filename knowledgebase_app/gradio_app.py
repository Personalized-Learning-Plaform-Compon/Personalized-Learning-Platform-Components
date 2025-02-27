# gradio_app.py
import gradio as gr

def predict_quiz(topic):
    # For demonstration, generate a list of quiz questions.
    # Replace this with your actual model call or logic.
    questions = [f"Question {i+1} for '{topic}': What is ... ?" for i in range(5)]
    return questions

iface = gr.Interface(
    fn=predict_quiz,
    inputs="text",
    outputs="json",
    title="Quiz Generator",
    description="Generates quiz questions based on the given topic."
)

if __name__ == "__main__":
    # Launch the Gradio server on localhost at port 7860.
    iface.launch(server_name="127.0.0.1", server_port=7860)
