"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template
from PrivacyRA import app


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/payment')
def payment():
    return render_template('payment_form.html')


@app.route('/payment_success')
def payment_success():
    return "Payment successful!"

@app.route('/request')
def request():
    return render_template('request.html')

@app.route('/deleterequest')
def deleterequest():
    return render_template('deleterequest.html')

@app.route('/delete_formrequest_success')
def delete_formrequest_success():
    return render_template('delete_formrequest_success.html')#"Your request has been submitted successfully. We will review it shortly."

