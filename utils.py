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
        msg.attach(MIMEText(body, 'plain'))

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
body = 'Hello, this is a test email.'
smtp_server = 'smtp.gmail.com'
smtp_port = 587  # For Gmail
sender_password = 'gdnt kgzh hryt tclh'  # For Gmail use App password if 2FA is enabled

# send_email(sender_email, recipient_email, subject, body, smtp_server, smtp_port, sender_password)
