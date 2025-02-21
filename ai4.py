from fastapi import FastAPI, HTTPException
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import pandas as pd
import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# Load application details from JSON
with open("applications.json", "r") as f:
    applications_data = json.load(f)
    applications = applications_data["applications"]

# Load ServiceNow ticket data
ticket_data = pd.read_csv("servicenow_tickets.csv").fillna("Unknown")

# SQLite Database Setup
DB_PATH = "assessment_results.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    application TEXT,
    responses TEXT,
    ai_questions TEXT,
    user_answers TEXT,
    score REAL
)
""")
conn.commit()

# Load Phi-2 Model
MODEL_PATH = "C:/Users/YourUsername/phi-2/"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float32)

# Static Self-Assessment Questions
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

@app.post("/store-self-assessment")
def store_self_assessment(payload: dict):
    """Stores the self-assessment ratings before AI generates questions."""
    user = payload["user"]
    application = payload["application"]
    responses = json.dumps(payload["responses"])

    # Insert into SQLite
    cursor.execute("INSERT INTO assessments (user, application, responses, ai_questions, user_answers, score) VALUES (?, ?, ?, ?, ?, ?)", 
                   (user, application, responses, "[]", "[]", None))
    conn.commit()

    return {"message": "Self-assessment stored successfully"}

@app.post("/verify-skill")
def verify_skill(payload: dict):
    """Generates AI questions based on past tickets & application details and calculates score."""
    user = payload["user"]
    application = payload["application"]
    user_answers = payload["user_answers"]

    # Fetch application details
    if application not in applications:
        raise HTTPException(status_code=400, detail="Application not found")

    app_details = applications[application]
    functionality = app_details.get("functionality", "Unknown functionality")
    criticality = app_details.get("criticality", "Unknown criticality")
    common_issues = app_details.get("common_issues", [])

    # Generate AI questions
    input_prompt = (
        f"User is being assessed for {application}. "
        f"This application handles: {functionality}. "
        f"Criticality: {criticality}. "
        f"Common issues: {', '.join(common_issues)}. "
        f"Generate 5 advanced assessment questions."
    )

    inputs = tokenizer(input_prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(**inputs, max_length=200)
    questions = tokenizer.decode(output[0], skip_special_tokens=True).split("\n")

    # Calculate score (Basic logic: % correct answers)
    correct_answers = sum(1 for ans in user_answers if ans.lower() in ["yes", "correct"])
    score = (correct_answers / len(user_answers)) * 100 if user_answers else 0

    # Store in database
    cursor.execute("UPDATE assessments SET ai_questions=?, user_answers=?, score=? WHERE user=? AND application=?", 
                   (json.dumps(questions), json.dumps(user_answers), score, user,