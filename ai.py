# backend.py - FastAPI Backend for AI Verification

from fastapi import FastAPI, HTTPException
import logging
import json
import random

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_ticket_data():
    """Load ticket data from a JSON or database (dummy data here)"""
    return [
        {"task_number": "INC001", "application": "App1", "assigned_to": "John Doe", "close_notes": "Resolved issue X", "priority": 3},
        {"task_number": "INC002", "application": "App2", "assigned_to": "Jane Smith", "close_notes": "Fixed database error", "priority": 5},
        {"task_number": "INC003", "application": "App1", "assigned_to": "John Doe", "close_notes": "Patched security issue", "priority": 4}
    ]

def generate_questions(application, score):
    """Generate dynamic questions based on application and score."""
    question_bank = {
        "App1": [
            "What steps did you take to resolve a security issue?",
            "How do you handle performance issues in App1?"
        ],
        "App2": [
            "What are common database errors in App2?",
            "Explain a troubleshooting step for App2 crashes."
        ]
    }
    
    difficulty_factor = min(5, max(1, score))  # Keep score within 1-5
    selected_questions = random.sample(question_bank.get(application, ["Describe a challenge you faced."]), k=min(len(question_bank.get(application, [])), difficulty_factor))
    return selected_questions

@app.post("/verify-skill")
def verify_skill(user: str, application: str, score: int):
    """Verify employee skill score and generate questions."""
    tickets = load_ticket_data()
    user_tickets = [t for t in tickets if t["assigned_to"] == user and t["application"] == application]
    
    if not user_tickets:
        logging.warning(f"No tickets found for user {user} in {application}.")
        return {"message": "No ticket history found, defaulting to general questions.", "questions": generate_questions(application, score)}
    
    return {"message": "Skill verified, here are your questions.", "questions": generate_questions(application, score)}


# frontend.py - Streamlit UI for Self-Assessment

import streamlit as st
import requests

def main():
    st.title("Self-Assignment Skill Verification Tool")
    
    user = st.text_input("Enter your name:")
    application = st.selectbox("Select Application:", ["App1", "App2"])  
    score = st.slider("Rate your skill (1-5):", 1, 5, 3)
    
    if st.button("Verify My Skill"):
        response = requests.post("http://localhost:8000/verify-skill", json={"user": user, "application": application, "score": score})
        if response.status_code == 200:
            data = response.json()
            st.write(data["message"])
            for q in data["questions"]:
                st.write(f"- {q}")
        else:
            st.error("Error verifying skill.")

if __name__ == "__main__":
    main()
