# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import os
from dotenv import load_dotenv

# Ensure .env exists; create a default if missing
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(dotenv_path):
    default_env = (
        "# SMTP Settings\n"
        "SMTP_SERVER=localhost\n"
        "SMTP_PORT=25\n"
        "SMTP_USERNAME=\n"
        "SMTP_PASSWORD=\n"
        "SMTP_USE_TLS=False\n"
    )
    with open(dotenv_path, 'w') as f:
        f.write(default_env)
    print(f".env file not found. A default .env has been created at {dotenv_path}. Please configure it and restart the application.")
    exit(1)

# Load environment variables
load_dotenv(dotenv_path)

# Read SMTP settings from environment\SMTP_SERVER = os.getenv('SMTP_SERVER', 'localhost')
SMTP_SERVER   = os.getenv('SMTP_SERVER', 'localhost')
SMTP_PORT     = int(os.getenv('SMTP_PORT', '25'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
USE_TLS       = os.getenv('SMTP_USE_TLS', 'False').lower() in ('true', '1', 'yes')

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Ensure email template directory exists
os.makedirs(os.path.join(app.root_path, 'templates', 'email_templates'), exist_ok=True)

def extract_first_name(full_name):
    """Extract first name from a full name or email address"""
    if not full_name:
        return ""
    if "@" in full_name:
        username = full_name.split('@')[0]
        return username.split('.')[0].capitalize()
    return full_name.split()[0].capitalize()

@app.route('/')
def index():
    # List available email templates
    template_dir = os.path.join(app.root_path, 'templates', 'email_templates')
    templates = [f for f in os.listdir(template_dir) if f.endswith('.html')]

    # Pass SMTP defaults into the form
    return render_template(
        'index.html',
        templates=templates,
        smtp_server=SMTP_SERVER,
        smtp_port=SMTP_PORT,
        smtp_username=SMTP_USERNAME,
        use_tls=USE_TLS
    )

@app.route('/send', methods=['POST'])
def send_email():
    # Gather form data
    template_name   = request.form['template']
    from_email      = request.form['from_email']
    from_name       = request.form['from_name']
    envelope_from   = request.form.get('envelope_from') or from_email
    to_email        = request.form['to_email']
    subject         = request.form['subject']
    recipient_name  = request.form.get('recipient_name', '')
    action_url      = request.form.get('action_url')

    # Personalize recipient first name
    recipient_first = extract_first_name(recipient_name) or extract_first_name(to_email)

    # Render HTML template
    html_content = render_template(
        f'email_templates/{template_name}',
        recipient_first_name=recipient_first,
        recipient_email=to_email,
        action_url=action_url
    )

    # Show preview
    return render_template(
        'preview.html',
        from_email=from_email,
        from_name=from_name,
        envelope_from=envelope_from,
        to_email=to_email,
        subject=subject,
        html_content=html_content
    )

@app.route('/confirm_send', methods=['POST'])
def confirm_send():
    # Retrieve data from preview form
    from_email    = request.form['from_email']
    from_name     = request.form['from_name']
    envelope_from = request.form.get('envelope_from') or from_email
    to_email      = request.form['to_email']
    subject       = request.form['subject']
    html_content  = request.form['html_content']

    # Build MIME message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = formataddr((from_name, from_email))
    msg['To']      = to_email
    msg.attach(MIMEText(html_content, 'html'))

    try:
        print(f"→ Connecting to SMTP_SERVER={SMTP_SERVER!r} on port {SMTP_PORT}")
        # Connect to SMTP relay
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        if USE_TLS:
            server.starttls()
            server.ehlo()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        # Send email with custom envelope
        server.sendmail(envelope_from, [to_email], msg.as_string())
        server.quit()
        flash('Email sent successfully!', 'success')
    except Exception as e:
        flash(f'Error sending email: {e}', 'error')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
