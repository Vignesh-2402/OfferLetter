from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SubmitField
from wtforms.validators import DataRequired, Email

class CandidateForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    role = StringField("Role", validators=[DataRequired()])
    start_date = DateField("Start Date", format="%Y-%m-%d")
    submit = SubmitField("Add Candidate")
