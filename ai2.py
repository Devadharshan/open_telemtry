from fastapi import FastAPI, HTTPException
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import pandas as pd
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# Load application details from JSON
APPLICATIONS_JSON = "applications.json"
if not os.path.exists(APPLICATIONS_JSON):
    raise FileNotFoundError("applications.json not found!")

with open(APPLICATIONS_JSON, "r") as f:
    applications_data = json.load(f)
    applications = applications_data["applications"]

# Load ServiceNow ticket data
TICKETS_CSV = "servicenow_tickets.csv"
if not os.path.exists(TICKETS_CSV):
    raise FileNotFoundError("servicenow_tickets.csv not found!")

ticket_data = pd.read_csv(TICKETS_CSV).fillna("Unknown")  # Handle missing values

# Load Phi-2 Model
MODEL_PATH = "C:/Users/YourUsername/phi-2/"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("Phi-2 model path not found!")

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
    """Returns the list of applications."""
    return {"applications": list(applications.keys())}

@app.get("/static-questions")
def get_static_questions():
    """Returns the static self-assessment questions."""
    return {"questions": STATIC_QUESTIONS}

@app.post("/verify-skill")
def verify_skill(payload: dict):
    """AI verifies user's skill level based on ServiceNow tickets & application details."""
    user = payload.get("user")
    application = payload.get("application")
    responses = payload.get("responses")

    if not user or not application or not responses:
        raise HTTPException(status_code=400, detail="Invalid request. Missing required fields.")

    if application not in applications:
        raise HTTPException(status_code=400, detail="Application not found.")

    # Fetch tickets for selected application
    app_tickets = ticket_data[ticket_data["application"] == application]
    logging.info(f"Found {len(app_tickets)} tickets for application {application}")

    # Fetch application details
    app_details = applications.get(application, {})
    functionality = app_details.get("functionality", "Unknown functionality")
    criticality = app_details.get("criticality", "Unknown criticality")
    common_issues = app_details.get("common_issues", [])

    # AI Prompt for Generating Questions
    input_prompt = (
        f"User rated themselves {responses} in {application}. "
        f"This application handles: {functionality}. "
        f"It has a criticality level of {criticality}. "
        f"Common issues include: {', '.join(common_issues)}. "
        f"Based on past ServiceNow tickets, generate 5 advanced questions."
    )

    inputs = tokenizer(input_prompt, return_tensors="pt")
    with torch.no_grad():
        output = model.generate(**inputs, max_length=200)

    questions = tokenizer.decode(output[0], skip_special_tokens=True).split("\n")

    return {"questions": [q for q in questions if q.strip()]}




json : 

{
  "applications": {
    "App1": {
      "functionality": "Handles customer orders and inventory management.",
      "criticality": "High",
      "common_issues": [
        "Order processing failures",
        "Inventory sync issues",
        "Payment gateway errors"
      ]
    },
    "App2": {
      "functionality": "Manages employee payroll and HR operations.",
      "criticality": "Medium",
      "common_issues": [
        "Salary miscalculations",
        "Leave balance discrepancies",
        "Access control issues"
      ]
    },
    "App3": {
      "functionality": "Provides real-time monitoring of server performance.",
      "criticality": "Critical",
      "common_issues": [
        "High CPU usage alerts",
        "Memory leak detections",
        "Unexpected downtime incidents"
      ]
    },
    "App4": {
      "functionality": "Facilitates online customer support and ticketing.",
      "criticality": "High",
      "common_issues": [
        "Delayed ticket responses",
        "Incorrect issue categorization",
        "Automation rule failures"
      ]
    }
  }
}




run :

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

