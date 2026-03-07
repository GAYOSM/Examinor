from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import io
import urllib.parse
import streamlit as st

def send_email(to_email, from_email, smtp_server, smtp_port, smtp_user, smtp_password, df):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = "Student Responses"

    message = "Please find the attached student responses."
    phone_number = "91XXXXXXXXXX"  # Country code + number, no +
    whatsapp_url = f"https://wa.me/{phone_number}?text={urllib.parse.quote(message)}"
    st.markdown(f"[Send via WhatsApp]({whatsapp_url})")

    msg.attach(MIMEText(message, 'plain'))

    # Convert DataFrame to CSV in memory
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    # Attach CSV
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(csv_buffer.read().encode('utf-8'))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="student_responses.csv"')
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        # Show error in Streamlit
        st.error(f"Failed to send email: {e}")
        return False

def send_whatsapp_message(phone_number, df):
    # Build a summary message with names and register numbers
    if df.empty:
        message = "No student responses yet."
    else:
        message_lines = ["Student Responses:"]
        for idx, row in df.iterrows():
            name = row.get("name", "N/A")
            reg_no = row.get("reg_no", "N/A")
            message_lines.append(f"{idx+1}. {name} (Reg No: {reg_no})")
        message = "\n".join(message_lines)
    whatsapp_url = f"https://wa.me/{phone_number}?text={urllib.parse.quote(message)}"
    st.markdown(f"[Send via WhatsApp]({whatsapp_url})")