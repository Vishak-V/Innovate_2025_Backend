import base64
import json
import re
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
from typing import List, LiteralString, Optional
from fastapi.middleware.cors import CORSMiddleware
from google.genai.types import HttpOptions, Part
import os
import uuid
from google import genai
from utils import send_email

# FastAPI app initialization
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

# genai.configure(api_key="AIzaSyBvz0nA9MB-6SaVRTi7SSJRvm7xzfBcT28")

# img = Image.open("pipe.png")
# model=genai.GenerativeModel('gemini-2.0-flash')
# response=model.generate_content(img)
# print(response.text)
client = genai.Client(api_key="AIzaSyBvz0nA9MB-6SaVRTi7SSJRvm7xzfBcT28")

# Middleware for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Ticket(BaseModel):
    title: str
    description: str
    priority: str
    category: str


ticket_prompt = """
Analyze the provided image and extract relevant details to generate an appropriate ticket.

If the image contains food items, create a food item request ticket with the following fields:

Title: A brief summary of the food item(s) identified.

Description: A request to add the food item(s) to the inventory.

Priority: Categorize the request as 'low', 'medium', or 'high' based on factors such as perishability or urgency.

Category: Identify the type of food (e.g., Fruits, Vegetables, Dairy, Meat, Snacks).

If the image contains a maintenance issue, create a maintenance ticket with the following fields:

Title: A brief summary of the issue.

Description: A detailed explanation of the problem.

Priority: Categorize the issue as 'low', 'medium', or 'high' based on its severity.

Category: Identify the type of maintenance required (e.g., Electrical, Plumbing, HVAC, Structural).

Return the extracted information in the following JSON format:

json

{
  "title": "<extracted_title>",
  "description": "<extracted_description>",
  "priority": "<extracted_priority>",
  "category": "<extracted_category>"
}
Ensure that the extracted data accurately represents the observed content in the image.
"""


class ImagePayload(BaseModel):
    image_base64: str


def decode_base64_image(base64_str: str) -> bytes:
    """Decode base64 string to raw image bytes."""
    base64_str = re.sub(
        r"^data:image/[^;]+;base64,", "", base64_str
    )  # Remove any image prefix
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
            model="gemini-2.0-flash",
            contents=[
                img,
                ticket_prompt,
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": Ticket,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")

    print("RESPONSE: " + response.text)
    # Process and return the response
    if response.text:
        return {"llm_response": response.text}
    else:
        raise HTTPException(
            status_code=500, detail="No response received from the model."
        )


class Poll(BaseModel):
    title: str
    description: str
    options: list[str]


poll_prompt = """
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
            model="gemini-2.0-flash",
            contents=[poll_prompt],
            config={
                "response_mime_type": "application/json",
                "response_schema": Poll,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    # Process and return the response
    if response.text:
        return {"llm_response": json.dump(response.text)}
    else:
        raise HTTPException(
            status_code=500, detail="No response received from the model."
        )


class TicketWithIds(BaseModel):
    id: str
    title: str
    description: str


class CreateTicketRequest(BaseModel):
    title: str
    description: str
    current_tickets: List[TicketWithIds]


create_ticket_prompt = """
Given a new ticket request and a list of existing tickets, identify tickets that are similar.
Most tickets will not be the same, but consider them similar if they overlap in title, description allowing for minor wording variations.

Input format:

json

{
  \"title\": \"<new_ticket_title>\",
  \"description\": \"<new_ticket_description>\",

  \"current_tickets\": [
    {
      \"id\": \"<existing_ticket_id>\",
      \"title\": \"<existing_ticket_title>\",
      \"description\": \"<existing_ticket_description>\",
    }
  ]
}
Analyze the new ticket against the current_tickets list and return the IDs of similar tickets based on textual closeness and semantic meaning.

Return the result in the following JSON format:

[\"<similar_ticket_id_1>\", \"<similar_ticket_id_2>\", ...]

If there are no similar tickets (which there won't be most of the time), return an empty list:
[]
"""


@app.post("/identify_duplicates/")
async def identify_duplicates(payload: CreateTicketRequest):
    """Identify duplicate tickets."""

    try:
        # Send the request to Gemini API
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[create_ticket_prompt + payload.model_dump_json()],
            config={
                "response_mime_type": "application/json",
                "response_schema": list[str],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    # Process and return the response
    if response.text:
        return {"llm_response": response.text}
    else:
        raise HTTPException(
            status_code=500, detail="No response received from the model."
        )


class Employee(BaseModel):
    id: str
    name: str
    email: str
    description: str


class DirectTicketRequest(BaseModel):
    id: str
    title: str
    description: str
    category: str
    priority: str

    employees_info: List[Employee]


class EmployeeId(BaseModel):
    assigned_employee_id: str


sender_email = "CGI.office.req@gmail.com"
smtp_server = "smtp.gmail.com"
smtp_port = 587  # For Gmail
sender_password = "gdnt kgzh hryt tclh"


def get_email(employee_id, employees_info: List[Employee]):
    """Get the email of the employee."""
    # Placeholder function for sending email
    # Implement your email sending logic here
    employee_email = None
    for employee in employees_info:
        if employee.id == employee_id:
            employee_email = employee.email
            break
    return employee_email


# def send_email(employee_id,employees_info:List[Employee]):
#     """Send an email to the employee."""
#     # Placeholder function for sending email
#     # Implement your email sending logic here
#     employee_email = None
#     print(employee_id)
#     for employee in employees_info:
#         if employee.id == employee_id:
#             employee_email = employee.email
#             break
#     print(f"Email sent to employee with ID: {employee_email}")


direct_ticket_prompt = """
Given a DirectTicketRequest containing ticket details and a list of employees, determine which employee is most likely to complete the ticket.

Each employee has a description detailing their expertise and responsibilities. The employee whose description best matches the ticket's title, description, priority, and category should be selected.

Input Format:
json

{
  "id": "<ticket_id>",
  "title": "<ticket_title>",
  "description": "<ticket_description>",

  "employees_info": [
    {
      "id": "<employee_id>",
      "name": "<employee_name>",
      "email": "<employee_email>",
      "description": "<employee_description>",
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

generate_body_prompt = """
Create an email body for a ticket assignment based on the following attributes:

title: The title of the ticket.

description: A detailed description of the issue or request.

priority: The priority level of the ticket (e.g., Low, Medium, High).

category: The category of the ticket (e.g., IT, HR, Maintenance).

employees_info: The information of the employee assigned to the ticket, including their name and email address.

Use the title, description, priority, and category to generate a professional email body that notifies the assigned employee of their new ticket.

This prompt is designed to receive the DirectTicketRequest object and generate an email body containing the ticket's details for the assigned employee.
"""


@app.post("/direct_ticket/")
async def direct_ticket(
    payload: DirectTicketRequest,
):
    """Direct a ticket to the appropriate department."""

    try:
        # Send the request to Gemini API
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[direct_ticket_prompt + payload.model_dump_json()],
            config={
                "response_mime_type": "application/json",
                "response_schema": EmployeeId,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    employee_id = response.text
    employee_id = json.loads(employee_id)["assigned_employee_id"]
    recipient_id = get_email(employee_id, payload.employees_info)

    body = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Ticket Assigned</title>
        <style>
            body {
                font-family: 'Helvetica Neue', Arial, sans-serif;
                background-color: #f8f9fa;
                margin: 0;
                padding: 0;
                color: #333;
            }
            .container {
                width: 70%;
                margin: 50px auto;
                background-color: #ffffff;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                border-top: 5px solid #007BFF;
            }
            .header {
                background-color: #007BFF;
                color: #ffffff;
                text-align: center;
                padding: 20px 0;
                border-radius: 10px 10px 0 0;
            }
            .header h2 {
                font-size: 28px;
                margin: 0;
            }
            .ticket-details {
                margin-top: 30px;
            }
            .ticket-details h3 {
                font-size: 24px;
                color: #333;
                margin-bottom: 10px;
            }
            .ticket-details p {
                font-size: 16px;
                line-height: 1.6;
                margin: 10px 0;
            }
            .ticket-details p strong {
                color: #007BFF;
            }
            .priority {
                font-weight: bold;
                color: #e74c3c;
            }
            .description {
                margin-top: 20px;
                padding: 15px;
                background-color: #f7f7f7;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                line-height: 1.6;
                color: #555;
            }
            .cta-button {
                display: inline-block;
                background-color: #28a745;
                color: #fff;
                padding: 15px 30px;
                border-radius: 5px;
                font-size: 18px;
                text-decoration: none;
                font-weight: bold;
                text-align: center;
                margin-top: 30px;
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
                transition: background-color 0.3s ease;
            }
            .cta-button:hover {
                background-color: #218838;
            }
            .footer {
                margin-top: 40px;
                text-align: center;
                color: #888;
                font-size: 14px;
            }
            .footer a {
                color: #007BFF;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>New Ticket Assigned</h2>
            </div>
            <div class="ticket-details">
                <h3>Ticket Title: {{ title }}</h3>
                <p><strong>Category:</strong> {{ category }}</p>
                <p><strong>Priority:</strong> <span class="priority">{{ priority }}</span></p>
                <div class="description">
                    <h4>Description:</h4>
                    <p>{{ description }}</p>
                </div>
            </div>
            <a href={{ completed_link }} class="cta-button" role="button">Mark as Completed</a>
            <div class="footer">
                <p>If you have any questions, feel free to <a href="mailto:support@company.com">contact support</a>.</p>
            </div>
        </div>
    </body>
    </html>
    """
    body = body.replace("{{ title }}", payload.title)
    body = body.replace("{{ description }}", payload.description)
    body = body.replace("{{ category }}", payload.category)
    body = body.replace("{{ priority }}", payload.priority)
    body = body.replace(
        "{{ completed_link }}", "https://ua-innovate-25.vercel.app/ticket/" + payload.id
    )
    send_email(
        sender_email,
        recipient_id,
        f"Ticket: {payload.title} has been assigned to you.",
        body,
        smtp_server,
        smtp_port,
        sender_password,
    )

    return {"message": " email sent to employee id: " + employee_id}


class EmailNotification(BaseModel):
    recipient_email: List[str]
    subject: str
    body: str


@app.post("/send_email/")
async def send_email_notification(notification: EmailNotification):
    """Send an email notification."""
    for email in notification.recipient_email:
        try:
            send_email(
                sender_email,
                email,
                notification.subject,
                notification.body,
                smtp_server,
                smtp_port,
                sender_password,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error sending email: {e}")
    return {"message": "Emails sent successfully!"}


class TicketsForShoppingList(BaseModel):
    current_tickets: List[TicketWithIds]


class Item(BaseModel):
    name: str
    quantity: int
    priority: str


class ShoppingListResponse(BaseModel):
    shopping_list: List[Item]


shopping_list_prompt = """
Convert the given TicketsForShoppingList object into a list of Item objects. Each ticket in tickets represents a potential shopping list item, but only include tickets that clearly describe a shopping item.

For each valid shopping item. Only include items that can be purchased in a grocery store.:

name: Derived from the title of the ticket just the name of the item.

quantity: Depending on the item something that an office of 200 people would need.

priority: Remains the same as in the ticket.

Ignore tickets that do not reference a specific shopping item.

Return a list of Item objects in JSON format:

json

[
  {
    "name": "<extracted_name>",
    "quantity": <extracted_quantity>,
    "priority": "<extracted_priority>"
  }
]
Ensure that only relevant shopping items are included in the final output.
"""


@app.post("/shopping_list/")
async def shopping_list(payload: TicketsForShoppingList):
    """Generate a shopping list."""

    try:
        # Send the request to Gemini API
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[shopping_list_prompt + payload.model_dump_json()],
            config={
                "response_mime_type": "application/json",
                "response_schema": list[Item],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating content: {e}")

    # Process and return the response
    if response.text:
        return {"llm_response": response.text}
    else:
        raise HTTPException(
            status_code=500, detail="No response received from the model."
        )
