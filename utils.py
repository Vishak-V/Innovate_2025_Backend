import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(sender_email, recipient_email, subject, body, smtp_server, smtp_port, sender_password):
    try:
        # Create the email content
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Attach the body with the msg
        msg.attach(MIMEText(body, 'html'))

        # Set up the server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        
        # Login to the server using email credentials
        server.login(sender_email, sender_password)
        
        # Send the email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        
        # Quit the server
        server.quit()
        print("Email sent successfully!")

    except Exception as e:
        print(f"Error: {e}")

# Usage
sender_email = 'CGI.office.req@gmail.com'
recipient_email = 'vvikranth@crimson.ua.edu'
subject = 'Test Email'
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
        <a href="https://www.google.com/" class="cta-button" role="button">Mark as Completed</a>
        <div class="footer">
            <p>If you have any questions, feel free to <a href="mailto:support@company.com">contact support</a>.</p>
        </div>
    </div>
</body>
</html>



"""
smtp_server = 'smtp.gmail.com'
smtp_port = 587  # For Gmail
sender_password = 'gdnt kgzh hryt tclh'  # For Gmail use App password if 2FA is enabled

#send_email(sender_email, recipient_email, subject, body, smtp_server, smtp_port, sender_password)
