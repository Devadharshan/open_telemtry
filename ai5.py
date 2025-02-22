from fastapi import FastAPI, HTTPException
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import pandas as pd
import sqlite3
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# Load application details
with open("applications.json", "r") as f:
    applications_data = json.load(f)
    applications = applications_data["applications"]

# Load ServiceNow ticket data
ticket_data = pd.read_csv("servicenow_tickets.csv").fillna("Unknown")  # Handle missing values

# Initialize database
conn = sqlite3.connect("self_assessment.db", check_same_thread=False)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        application TEXT,
        responses TEXT,
        ai_questions TEXT,
        ai_answers TEXT,
        score REAL
    )
""")
conn.commit()

# Load Phi-2 Model (CPU-only)
MODEL_PATH = "C:/Users/YourUsername/phi-2/"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float32)

# Static self-assessment questions
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

    # Fetch past ServiceNow tickets
    app_tickets = ticket_data[ticket_data["application"] == application]

    # Fetch application details
    app_details = applications.get(application, {})
    functionality = app_details.get("functionality", "Unknown functionality")
    criticality = app_details.get("criticality", "Unknown criticality")
    common_issues = app_details.get("common_issues", [])

    # AI Prompt
    input_prompt = f"""
    The user rated themselves {responses} for {application}.
    Application functionality: {functionality}.
    Criticality: {criticality}.
    Common issues: {', '.join(common_issues)}.

    ServiceNow tickets:
    {app_tickets.head(5).to_string(index=False)}

    Generate 5 technical validation questions to assess the user’s expertise in {application}.
    """
    
    inputs = tokenizer(input_prompt, return_tensors="pt")

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_length=150,
            num_return_sequences=1,
            temperature=0.3,
            top_p=0.8,
            eos_token_id=tokenizer.eos_token_id
        )

    questions = tokenizer.decode(output[0], skip_special_tokens=True).split("\n")
    filtered_questions = [q for q in questions if q.strip()]

    return {"questions": filtered_questions}

@app.post("/submit-assessment")
def submit_assessment(payload: dict):
    user = payload["user"]
    application = payload["application"]
    responses = payload["responses"]
    ai_questions = payload["ai_questions"]
    ai_answers = payload["ai_answers"]
    
    # Calculate score (simple percentage for now)
    correct_answers = sum(1 for ans in ai_answers if ans.lower() in ["yes", "correct"])
    score = (correct_answers / len(ai_answers)) * 100 if ai_answers else 0

    cursor.execute("""
        INSERT INTO assessments (user, application, responses, ai_questions, ai_answers, score)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user, application, json.dumps(responses), json.dumps(ai_questions), json.dumps(ai_answers), score))
    conn.commit()

    return {"message": "Assessment submitted successfully", "score": score}

@app.get("/manager-view")
def get_assessments():
    cursor.execute("SELECT * FROM assessments")
    data = cursor.fetchall()
    return {"assessments": data}





--ui



import streamlit as st
import requests
import json
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_URL = "http://localhost:8000"

st.title("🔍 Self-Assessment Tool")

# Fetch applications
apps = requests.get(f"{API_URL}/applications").json()["applications"]
selected_app = st.selectbox("Select an application", apps)

# Fetch static questions
static_questions = requests.get(f"{API_URL}/static-questions").json()["questions"]
responses = {}

st.subheader("📌 Self-Assessment Questions")
for q in static_questions:
    responses[q] = st.slider(q, 1, 5, 3)

if st.button("Submit Self-Assessment"):
    payload = {
        "user": "TestUser",
        "application": selected_app,
        "responses": list(responses.values())
    }

    # Get AI-generated questions
    ai_response = requests.post(f"{API_URL}/verify-skill", json=payload)
    if ai_response.status_code == 200:
        ai_questions = ai_response.json()["questions"]
        st.session_state["ai_questions"] = ai_questions
        st.session_state["responses"] = responses
        st.session_state["submitted"] = True
    else:
        st.error("Error generating AI questions")

if "submitted" in st.session_state:
    st.subheader("🤖 AI-Generated Questions")
    ai_answers = []
    for q in st.session_state["ai_questions"]:
        ai_answers.append(st.text_input(q))

    if st.button("Submit AI Responses"):
        submit_payload = {
            "user": "TestUser",
            "application": selected_app,
            "responses": list(st.session_state["responses"].values()),
            "ai_questions": st.session_state["ai_questions"],
            "ai_answers": ai_answers
        }
        submit_response = requests.post(f"{API_URL}/submit-assessment", json=submit_payload)
        if submit_response.status_code == 200:
            st.success(f"Assessment submitted! Score: {submit_response.json()['score']}%")

# Manager View
st.subheader("📊 Manager View")
if st.button("View Assessments"):
    data = requests.get(f"{API_URL}/manager-view").json()["assessments"]
    st.table(data)




prompt = f"""
You are an AI assistant evaluating a support engineer's expertise on the application: {application_name}.

**Task:**  
- Read the provided application details and ticket history.  
- Generate **5 relevant, non-repetitive questions** based on the support tickets.  
- Ensure each question tests practical troubleshooting skills.  

### **Application Details:**  
{application_details}  

### **Past Tickets & Issues:**  
{csv_data}  

**Now, generate 5 structured questions for evaluation.**  
"""
