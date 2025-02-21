from fastapi import FastAPI, HTTPException
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# Database setup
DB_PATH = "assessment_results.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        application TEXT,
        selected_scores TEXT,
        ai_questions TEXT,
        user_answers TEXT,
        ai_score INTEGER
    )
""")
conn.commit()

# Load application details
with open("applications.json", "r") as f:
    applications_data = json.load(f)
    applications = applications_data["applications"]

# Load AI Model (CPU Only)
MODEL_PATH = "C:/Users/YourUsername/phi-2/"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float32)

# Static Questions
STATIC_QUESTIONS = [
    "How familiar are you with the core infrastructure of this application?",
    "Have you resolved any critical issues related to this application?",
    "How well do you understand its functionalities and dependencies?",
    "Have you worked on performance optimization for this application?",
    "Can you troubleshoot complex failures in this application?"
]

@app.get("/applications")
def get_applications():
    return {"applications": list(applications.keys())}

@app.get("/static-questions")
def get_static_questions():
    return {"questions": STATIC_QUESTIONS}

@app.post("/verify-skill")
def verify_skill(payload: dict):
    user = payload["user"]
    application = payload["application"]
    responses = payload["responses"]

    if application not in applications:
        raise HTTPException(status_code=400, detail="Application not found")

    # AI-Based Question Generation
    input_prompt = (
        f"User rated themselves {responses} in {application}. "
        f"Generate 5 advanced questions."
    )

    inputs = tokenizer(input_prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(**inputs, max_length=200)
    questions = tokenizer.decode(output[0], skip_special_tokens=True).split("\n")

    return {"questions": [q for q in questions if q.strip()]}

@app.post("/store-assessment")
def store_assessment(payload: dict):
    user = payload["user"]
    application = payload["application"]
    selected_scores = json.dumps(payload["selected_scores"])
    ai_questions = json.dumps(payload["ai_questions"])
    user_answers = json.dumps(payload["user_answers"])

    # AI Scoring Logic
    correct_answers = sum(1 for ans in payload["user_answers"] if ans.lower() in ["yes", "correct"])
    ai_score = (correct_answers / len(payload["ai_questions"])) * 100

    # Store in DB
    try:
        cursor.execute(
            "INSERT INTO assessments (user, application, selected_scores, ai_questions, user_answers, ai_score) VALUES (?, ?, ?, ?, ?, ?)",
            (user, application, selected_scores, ai_questions, user_answers, ai_score)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"DB Insert Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store assessment")

    return {"message": "Assessment stored successfully", "ai_score": ai_score}

@app.get("/manager-view")
def get_assessments():
    try:
        cursor.execute("SELECT * FROM assessments")
        rows = cursor.fetchall()
        return {"assessments": rows}
    except Exception as e:
        logging.error(f"DB Read Error: {e}")
        return {"error": str(e)}






-- ui cide

import streamlit as st
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_URL = "http://127.0.0.1:8000"

# Load Applications
st.title("Self-Assessment App")
response = requests.get(f"{API_URL}/applications")
applications = response.json()["applications"]

# Select Application
application = st.selectbox("Select an Application:", applications)

# Fetch Static Questions
response = requests.get(f"{API_URL}/static-questions")
static_questions = response.json()["questions"]

# Display Static Questions
st.subheader("Self-Assessment")
selected_scores = {}
for question in static_questions:
    score = st.slider(question, 1, 5, 3)
    selected_scores[question] = score

# Submit Button
if st.button("Submit Self-Assessment"):
    payload = {
        "user": "John Doe",
        "application": application,
        "responses": list(selected_scores.values())
    }
    response = requests.post(f"{API_URL}/verify-skill", json=payload)

    if response.status_code == 200:
        ai_questions = response.json()["questions"]
        st.subheader("AI-Generated Questions")
        user_answers = []

        for question in ai_questions:
            answer = st.text_input(question)
            user_answers.append(answer)

        if st.button("Submit AI Assessment"):
            final_payload = {
                "user": "John Doe",
                "application": application,
                "selected_scores": selected_scores,
                "ai_questions": ai_questions,
                "user_answers": user_answers
            }
            response = requests.post(f"{API_URL}/store-assessment", json=final_payload)
            if response.status_code == 200:
                st.success("Assessment Stored Successfully!")
            else:
                st.error("Error Storing Assessment")

# Manager View
if st.button("Manager View"):
    response = requests.get(f"{API_URL}/manager-view")
    if response.status_code == 200:
        assessments = response.json()["assessments"]
        st.write(assessments)

