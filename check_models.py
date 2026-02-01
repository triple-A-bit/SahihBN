import google.generativeai as genai
import os

# Put your API KEY here directly just to test
API_KEY = "AIzaSyBAQgH9k4xw8ZY5vC7Jiut4XGcwh5JMSdg"
genai.configure(api_key=API_KEY)

print("List of available models for you:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
