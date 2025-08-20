from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    role = db.Column(db.String(150))
    start_date = db.Column(db.Date)  # Date type for start_date
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="pending")
    offer_pdf = db.Column(db.String(200), nullable=True)
    certificate_pdf = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<Candidate {self.id} {self.name}>"
