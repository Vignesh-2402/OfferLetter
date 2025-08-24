import os
import base64
import traceback
from flask import Flask, render_template, redirect, url_for, flash, send_from_directory, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DateField
from wtforms.validators import DataRequired, Email
from datetime import datetime
import pdfkit
from flask_mail import Mail, Message

# ---------------- CONFIG ---------------- #
class Config:
    SECRET_KEY = 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = 'smtp-relay.brevo.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = '9453b1001@smtp-brevo.com'
    MAIL_PASSWORD = 'hMBXVg6bG1yNjYWa'
    MAIL_DEFAULT_SENDER = ('Automation', 'vv76409727@gmail.com')

# ---------------- APP INIT ---------------- #
app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
mail = Mail(app)

# Folders
GENERATED_PDFS_FOLDER = os.path.join(os.path.dirname(__file__), "generated_pdfs")
os.makedirs(GENERATED_PDFS_FOLDER, exist_ok=True)

# PDFKit config
WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
pdfkit_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

# ---------------- MODELS ---------------- #
class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120))
    start_date = db.Column(db.Date)
    status = db.Column(db.String(50))
    offer_pdf = db.Column(db.String(200))
    certificate_pdf = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- FORMS ---------------- #
class CandidateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    role = StringField("Role")
    start_date = DateField("Start Date", format='%Y-%m-%d')

# ---------------- DB INIT ---------------- #
with app.app_context():
    db.create_all()

# ---------------- HELPERS ---------------- #
def send_email_with_pdf(candidate, pdf_filename, subject, body):
    try:
        filepath = os.path.join(GENERATED_PDFS_FOLDER, pdf_filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Attachment not found: {filepath}")

        msg = Message(subject=subject, recipients=[candidate.email])
        msg.body = body
        with open(filepath, "rb") as fp:
            msg.attach(pdf_filename, "application/pdf", fp.read())

        mail.send(msg)
        print(f"✅ Email sent to {candidate.email}")
        return True
    except Exception:
        print("❌ Email sending failed!")
        traceback.print_exc()
        return False

def load_base64_logo():
    logo_path = os.path.join(app.static_folder, "automation_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    else:
        # Fallback to an online logo if local file missing
        fallback_url = "https://via.placeholder.com/200x60.png?text=Automation+Logo"
        import requests
        try:
            resp = requests.get(fallback_url, timeout=5)
            if resp.status_code == 200:
                return base64.b64encode(resp.content).decode('utf-8')
        except:
            pass
        return ""

def inline_css(filename):
    css_path = os.path.join(app.static_folder, filename)
    if not os.path.exists(css_path):
        raise FileNotFoundError(f"CSS file not found: {css_path}")
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_pdf(template_name, candidate, filename):
    base64_logo = load_base64_logo()
    css_content = inline_css("style.css")

    html = render_template(
        template_name,
        candidate=candidate,
        issue_date=datetime.today().strftime("%B %d, %Y"),
        current_year=datetime.today().year,
        base64_logo=base64_logo,
        css_content=css_content
    )

    filepath = os.path.join(GENERATED_PDFS_FOLDER, filename)
    options = {'enable-local-file-access': None}
    pdfkit.from_string(html, filepath, configuration=pdfkit_config, options=options)
    return filename

def generate_offer_pdf(candidate):
    return generate_pdf("offer_letter.html", candidate, f"offer_{candidate.id}.pdf")

def generate_certificate_pdf(candidate):
    return generate_pdf("certificate.html", candidate, f"certificate_{candidate.id}.pdf")

# ---------------- ROUTES ---------------- #
@app.route("/", methods=["GET", "POST"])
def index():
    form = CandidateForm()
    if form.validate_on_submit():
        candidate = Candidate(
            name=form.name.data,
            email=form.email.data,
            role=form.role.data,
            start_date=form.start_date.data
        )
        db.session.add(candidate)
        db.session.commit()
        flash("Candidate added successfully", "success")
        return redirect(url_for("index"))
    elif request.method == "POST":
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", "danger")

    candidates = Candidate.query.order_by(Candidate.created_at.desc()).all()

    # Pass logo to home UI
    base64_logo = load_base64_logo()

    return render_template("home.html", candidates=candidates, form=form, base64_logo=base64_logo)

@app.route("/generate_offer/<int:candidate_id>")
def generate_offer(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    filename = generate_offer_pdf(candidate)
    candidate.offer_pdf = filename
    candidate.status = "offer_generated"
    db.session.commit()
    flash("Offer letter generated successfully!", "success")
    return redirect(url_for("index"))

@app.route("/generate_certificate/<int:candidate_id>")
def generate_certificate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    filename = generate_certificate_pdf(candidate)
    candidate.certificate_pdf = filename
    candidate.status = "certificate_generated"
    db.session.commit()
    flash("Certificate generated successfully!", "success")
    return redirect(url_for("index"))

@app.route("/send_email/<int:candidate_id>/<string:doc_type>")
def send_email_route(candidate_id, doc_type):
    candidate = Candidate.query.get_or_404(candidate_id)

    if doc_type == "offer" and candidate.offer_pdf:
        pdf_filename = candidate.offer_pdf
        subject = "Your Offer Letter"
        body = f"Dear {candidate.name},\n\nPlease find attached your offer letter."
    elif doc_type == "certificate" and candidate.certificate_pdf:
        pdf_filename = candidate.certificate_pdf
        subject = "Your Completion Certificate"
        body = f"Dear {candidate.name},\n\nPlease find attached your completion certificate."
    else:
        flash("No document available to send.", "danger")
        return redirect(url_for("index"))

    if send_email_with_pdf(candidate, pdf_filename, subject, body):
        flash(f"✅ Email sent successfully to {candidate.email}!", "success")
    else:
        flash(f"❌ Failed to send email to {candidate.email}.", "danger")

    return redirect(url_for("index"))

@app.route("/delete_candidate/<int:candidate_id>", methods=["POST"])
def delete_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)

    if candidate.offer_pdf:
        offer_path = os.path.join(GENERATED_PDFS_FOLDER, candidate.offer_pdf)
        if os.path.exists(offer_path):
            os.remove(offer_path)

    if candidate.certificate_pdf:
        cert_path = os.path.join(GENERATED_PDFS_FOLDER, candidate.certificate_pdf)
        if os.path.exists(cert_path):
            os.remove(cert_path)

    db.session.delete(candidate)
    db.session.commit()

    flash(f"Candidate '{candidate.name}' removed successfully.", "success")
    return redirect(url_for("index"))

@app.route("/generated_pdfs/<path:filename>")
def download_generated(filename):
    return send_from_directory(GENERATED_PDFS_FOLDER, filename, as_attachment=True)

@app.route("/test_email")
def test_email():
    try:
        msg = Message(
            subject="Test Email from Flask",
            recipients=["vv76409727@gmail.com"],
            body="This is a test email sent from Flask using Brevo SMTP."
        )
        mail.send(msg)
        return "✅ Test email sent successfully!"
    except Exception as e:
        traceback.print_exc()
        return f"❌ Error sending test email: {e}"

if __name__ == "__main__":
    app.run(debug=True)
