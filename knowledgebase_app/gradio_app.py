# gradio_app.py
import gradio as gr

def predict_quiz(topic):
    # For demonstration, generate a list of quiz questions.
    questions = [f"Question {i+1} for '{topic}': What is ... ?" for i in range(5)]
    return questions

iface = gr.Interface(
    fn=predict_quiz,
    inputs="text",
    outputs="json",
    title="Quiz Generator",
    description="Generates quiz questions based on the given topic.",
    enable_api=True  # Ensure the API is enabled
)

if __name__ == "__main__":
    iface.launch(server_name="127.0.0.1", server_port=7860)
