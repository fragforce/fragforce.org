from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired


class ImageUploadForm(Form):
    title = StringField('Filename', validators=[DataRequired()])
    desc = StringField('Description', validators=[DataRequired()])
    published = BooleanField('Published')
    img = FileField('Image', validators=[FileRequired()])
