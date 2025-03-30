import base64
import json
import re
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
from typing import List,LiteralString, Optional
from fastapi.middleware.cors import CORSMiddleware
from google.genai.types import HttpOptions,Part
import os
import uuid
from google import genai
from utils import send_email

# FastAPI app initialization
app = FastAPI()

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

# genai.configure(api_key="AIzaSyBvz0nA9MB-6SaVRTi7SSJRvm7xzfBcT28")

# img = Image.open("pipe.png")
# model=genai.GenerativeModel('gemini-2.0-flash')
# response=model.generate_content(img)
# print(response.text)
client=genai.Client(api_key='AIzaSyBvz0nA9MB-6SaVRTi7SSJRvm7xzfBcT28')

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity; adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class Ticket(BaseModel):
    title: str
    description: str
    priority: str
    category: str



ticket_prompt="""
Analyze the provided image and extract relevant details to generate a maintenance ticket. The ticket should include the following fields:

Title: A brief summary of the issue.

Description: A detailed explanation of the problem.

Priority: Categorize the issue as 'Low', 'Medium', or 'High' based on its severity.

Category: Identify the type of maintenance required (e.g., Electrical, Plumbing, HVAC, Structural).

Return the extracted information in the following JSON format:

json

{
  \"title\": \"<extracted_title>\",
  \"description\": \"<extracted_description>\",
  \"priority\": \"<extracted_priority>\",
  \"category\": \"<extracted_category>\"
}
Ensure that the extracted data accurately represents the maintenance issue observed in the image.
"""





class ImagePayload(BaseModel):
    image_base64: str

def decode_base64_image(base64_str: str) -> bytes:
    """Decode base64 string to raw image bytes."""
    base64_str = re.sub(r"^data:image/[^;]+;base64,", "", base64_str)  # Remove any image prefix
    try:
        return base64.b64decode(base64_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 data: {e}")

@app.post("/process_image/")
async def process_image(payload: ImagePayload):
    """Process the image and generate a response using Gemini API."""

    image_str = payload.image_base64
    image_bytes = decode_base64_image(payload.image_base64)

    # Generate a random filename
    random_filename = f"{uuid.uuid4().hex}.png"
    file_path = os.path.join(TEMP_DIR, random_filename)

    try:
        # Validate and save image
        img = Image.open(BytesIO(image_bytes))
        img.save(file_path)
        print(f"Image saved: {file_path}")

        # Process the image (if needed)
        # Example: Getting image size
        width, height = img.size
        result = {"message": "Image processed", "width": width, "height": height}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")

    img = Image.open(file_path)

    try:
        # Send the request to Gemini API
        response = client.models.generate_content(

            model='gemini-2.0-flash',
            contents=[img,
                ticket_prompt,
                ],
            config={
                'response_mime_type': 'application/json',
                'response_schema': Ticket,
        },
        
    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
    # Process and return the response
    if response.text:
        return {"llm_response": response.text}
    else:
        raise HTTPException(status_code=500, detail="No response received from the model.")

class Poll(BaseModel):
    title: str
    description: str
    options: list[str]

poll_prompt="""
Generate a fun and engaging poll for an office community. The poll should include:

Title: A catchy and inviting name for the poll.

Description: A brief and engaging explanation of what the poll is about.

Options: A list of 3-5 possible responses that employees can choose from.

The poll should be lighthearted and relevant to an office setting, such as favorite work snacks, best desk setups, ideal break activities, or funniest email sign-offs.

Return the poll in the following JSON format:

json

{
  \"title\": \"<fun_poll_title>\",
  \"description\": \"<fun_poll_description>\",
  \"options\": [\"<option_1>\", \"<option_2>\", \"<option_3>\", \"<option_4>\", \"<option_5>\"]
}
Ensure the poll is enjoyable, inclusive, and encourages office participation!"""

@app.get("/poll/")
async def create_poll():
    """Generate a fun poll for the office."""

    try:
        # Send the request to Gemini API
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[poll_prompt],
            config={
                'response_mime_type': 'application/json',
                'response_schema': Poll,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    # Process and return the response
    if response.text:
        return {"llm_response": response.text}
    else:
        raise HTTPException(status_code=500, detail="No response received from the model.")
    
class TicketWithIds(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    category: str

class CreateTicketRequest(BaseModel):
    title: str
    description: str
    priority: str
    category: str
    current_tickets:List[TicketWithIds]

create_ticket_prompt = """
Given a new ticket request and a list of existing tickets, identify tickets that are very similar to the new request. Two tickets are considered similar if they have a high degree of overlap in their title, description, priority, and category. Minor variations in wording should still be considered a match.

The input format is as follows:

json

{
  \"title\": \"<new_ticket_title>\",
  \"description\": \"<new_ticket_description>\",
  \"priority\": \"<new_ticket_priority>\",
  \"category\": \"<new_ticket_category>\",
  \"current_tickets\": [
    {
      \"id\": \"<existing_ticket_id>\",
      \"title\": \"<existing_ticket_title>\",
      \"description\": \"<existing_ticket_description>\",
      \"priority\": \"<existing_ticket_priority>\",
      \"category\": \"<existing_ticket_category>\"
    },
  ]
}
Analyze the new ticket against the current_tickets list and return the IDs of tickets that are very similar. Consider similarity based on textual closeness, semantic meaning, and category relevance.

Return the result in the following JSON format:

json

{
  \"similar_ticket_ids\": [\"<similar_ticket_id_1>\", \"<similar_ticket_id_2>\", ...]
}
Ensure that the comparison accounts for minor wording differences and prioritizes meaningful matches."""


@app.post("/identify_duplicates/")
async def identify_duplicates(payload: CreateTicketRequest,):
    """Identify duplicate tickets."""
    try:
        # Send the request to Gemini API
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[create_ticket_prompt+payload.model_dump_json()],
            config={
                'response_mime_type': 'application/json',
                'response_schema': list[str],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    # Process and return the response
    if response.text:
        return {"llm_response": response.text}
    else:
        raise HTTPException(status_code=500, detail="No response received from the model.")

class Employee(BaseModel):
    name: str
    employee_id: str
    email: str
    description: str
    phone_number: str
    
class DirectTicketRequest(BaseModel):
    title: str
    description: str
    priority: str
    category: str
    employee_info:List[Employee]

class EmployeeId(BaseModel):
    assigned_employee_id: str

sender_email = 'CGI.office.req@gmail.com'
smtp_server = 'smtp.gmail.com'
smtp_port = 587  # For Gmail
sender_password = 'gdnt kgzh hryt tclh'

def get_email(employee_id,employee_info:List[Employee]):
    """Get the email of the employee."""
    # Placeholder function for sending email
    # Implement your email sending logic here
    employee_email = None
    for employee in employee_info:
        if employee.employee_id == employee_id:
            employee_email = employee.email
            break
    return employee_email

# def send_email(employee_id,employee_info:List[Employee]):
#     """Send an email to the employee."""
#     # Placeholder function for sending email
#     # Implement your email sending logic here
#     employee_email = None
#     print(employee_id)
#     for employee in employee_info:
#         if employee.employee_id == employee_id:
#             employee_email = employee.email
#             break
#     print(f"Email sent to employee with ID: {employee_email}")




direct_ticket_prompt="""
Given a DirectTicketRequest containing ticket details and a list of employees, determine which employee is most likely to complete the ticket.

Each employee has a description detailing their expertise and responsibilities. The employee whose description best matches the ticket's title, description, priority, and category should be selected.

Input Format:
json

{
  "title": "<ticket_title>",
  "description": "<ticket_description>",
  "priority": "<ticket_priority>",
  "category": "<ticket_category>",
  "employee_info": [
    {
      "name": "<employee_name>",
      "employee_id": "<employee_id>",
      "email": "<employee_email>",
      "description": "<employee_description>",
      "phone_number": "<employee_phone>"
    },
    ...
  ]
}
Output Format:
Return the employee ID of the most suitable employee in the following JSON format:

json

{
  "assigned_employee_id": "<best_fit_employee_id>"
}
Ensure that the selection is based on the most relevant experience and skills as described in the employee descriptions. If no clear match is found, return null.
"""

generate_body_prompt="""
Create an email body for a ticket assignment based on the following attributes:

title: The title of the ticket.

description: A detailed description of the issue or request.

priority: The priority level of the ticket (e.g., Low, Medium, High).

category: The category of the ticket (e.g., IT, HR, Maintenance).

employee_info: The information of the employee assigned to the ticket, including their name and email address.

Use the title, description, priority, and category to generate a professional email body that notifies the assigned employee of their new ticket.

This prompt is designed to receive the DirectTicketRequest object and generate an email body containing the ticket's details for the assigned employee.
"""

@app.post("/direct_ticket/")
async def direct_ticket(payload: DirectTicketRequest,):
    """Direct a ticket to the appropriate department."""

    try:
        # Send the request to Gemini API
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[direct_ticket_prompt+payload.model_dump_json()],
            config={
                'response_mime_type': 'application/json',
                'response_schema': EmployeeId,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")
    
    

    employee_id=response.text
    employee_id = json.loads(employee_id)["assigned_employee_id"]
    recipient_id=get_email(employee_id,payload.employee_info)
    send_email(sender_email, recipient_id, f"Ticket: {payload.title} has been assigned to you.", f"{payload.description}", smtp_server, smtp_port, sender_password)
    
    return {"message": " email sent to employee id: "+employee_id}