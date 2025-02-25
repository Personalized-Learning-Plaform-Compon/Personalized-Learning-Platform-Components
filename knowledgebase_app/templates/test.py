import unittest
import json
from app import app

class GenerateQuizTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_generate_quiz_default_questions(self):
        response = self.app.post('/generate_quiz', data=json.dumps({
            "topic_text": "The Earth revolves around the Sun."
        }), content_type='application/json')
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['quiz_questions']), 5)

    def test_generate_quiz_custom_questions(self):
        response = self.app.post('/generate_quiz', data=json.dumps({
            "topic_text": "The Earth revolves around the Sun.",
            "num_questions": 3
        }), content_type='application/json')
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['quiz_questions']), 3)

    def test_generate_quiz_missing_topic_text(self):
        response = self.app.post('/generate_quiz', data=json.dumps({}), content_type='application/json')
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], "Please provide a topic_text")

    def test_generate_quiz_empty_topic_text(self):
        response = self.app.post('/generate_quiz', data=json.dumps({
            "topic_text": ""
        }), content_type='application/json')
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], "Please provide a topic_text")

    def test_generate_quiz_long_topic_text(self):
        response = self.app.post('/generate_quiz', data=json.dumps({
            "topic_text": "The Earth revolves around the Sun. The Moon revolves around the Earth. The solar system consists of the Sun and all the objects that orbit it, including planets, moons, asteroids, and comets."
        }), content_type='application/json')
        
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['quiz_questions']), 5)

if __name__ == '__main__':
    unittest.main()