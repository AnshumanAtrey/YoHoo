import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import random
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///birthdays.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Models
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    birthday = db.Column(db.Date, nullable=False)
    profile_pic = db.Column(db.String(200), default='default.png')
    custom_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BirthdayWish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # funny, heartfelt, etc.

class GifCollection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    is_custom = db.Column(db.Boolean, default=False)

# Helper functions
def get_upcoming_birthdays(days=30):
    today = datetime.now().date()
    end_date = today + timedelta(days=days)
    
    upcoming = []
    contacts = Contact.query.all()
    
    for contact in contacts:
        # Calculate next birthday
        birthday = contact.birthday
        next_birthday = datetime(today.year, birthday.month, birthday.day).date()
        
        # If the birthday has already occurred this year, get next year's date
        if next_birthday < today:
            next_birthday = datetime(today.year + 1, birthday.month, birthday.day).date()
        
        # If within our range
        if next_birthday <= end_date:
            days_left = (next_birthday - today).days
            upcoming.append({
                'contact': contact,
                'next_birthday': next_birthday,
                'days_left': days_left
            })
    
    # Sort by days left
    upcoming.sort(key=lambda x: x['days_left'])
    return upcoming

def send_birthday_email(contact, gif_url=None):
    sender_email = os.getenv('EMAIL_USER')
    sender_password = os.getenv('EMAIL_PASSWORD')
    
    if not sender_email or not sender_password:
        flash('Email credentials not configured', 'danger')
        return False
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = contact.email
    msg['Subject'] = f"Happy Birthday, {contact.name}!"
    
    # Message body
    message = contact.custom_message or f"Happy Birthday, {contact.name}! Wishing you a fantastic day filled with joy and happiness."
    msg.attach(MIMEText(message, 'plain'))
    
    # Attach GIF if provided
    if gif_url:
        try:
            response = requests.get(gif_url)
            if response.status_code == 200:
                gif_data = response.content
                image = MIMEImage(gif_data)
                image.add_header('Content-Disposition', 'attachment', filename='birthday_gif.gif')
                msg.attach(image)
        except Exception as e:
            print(f"Error attaching GIF: {e}")
    
    # Send email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def get_random_wish(category=None):
    if category:
        wishes = BirthdayWish.query.filter_by(category=category).all()
    else:
        wishes = BirthdayWish.query.all()
    
    if wishes:
        return random.choice(wishes).message
    return "Happy Birthday! Wishing you all the best on your special day!"

def get_random_gif(category=None):
    if category:
        gifs = GifCollection.query.filter_by(category=category).all()
    else:
        gifs = GifCollection.query.all()
    
    if gifs:
        return random.choice(gifs).url
    return None

# Routes
@app.route('/')
def index():
    upcoming = get_upcoming_birthdays()
    return render_template('index.html', upcoming=upcoming, app_name="YoHoo")

@app.route('/contacts')
def contacts():
    all_contacts = Contact.query.order_by(Contact.name).all()
    return render_template('contacts.html', contacts=all_contacts, app_name="YoHoo")

@app.route('/add_contact', methods=['GET', 'POST'])
def add_contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        birthday = datetime.strptime(request.form.get('birthday'), '%Y-%m-%d').date()
        custom_message = request.form.get('custom_message')
        
        # Handle profile picture upload
        profile_pic = 'default.png'
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_pic = filename
        
        new_contact = Contact(
            name=name,
            email=email,
            phone=phone,
            birthday=birthday,
            profile_pic=profile_pic,
            custom_message=custom_message
        )
        
        db.session.add(new_contact)
        db.session.commit()
        
        flash('Contact added successfully!', 'success')
        return redirect(url_for('contacts'))
    
    return render_template('add_contact.html', app_name="YoHoo")

@app.route('/edit_contact/<int:id>', methods=['GET', 'POST'])
def edit_contact(id):
    contact = Contact.query.get_or_404(id)
    
    if request.method == 'POST':
        contact.name = request.form.get('name')
        contact.email = request.form.get('email')
        contact.phone = request.form.get('phone')
        contact.birthday = datetime.strptime(request.form.get('birthday'), '%Y-%m-%d').date()
        contact.custom_message = request.form.get('custom_message')
        
        # Handle profile picture upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                contact.profile_pic = filename
        
        db.session.commit()
        flash('Contact updated successfully!', 'success')
        return redirect(url_for('contacts'))
    
    return render_template('edit_contact.html', contact=contact, app_name="YoHoo")

@app.route('/delete_contact/<int:id>')
def delete_contact(id):
    contact = Contact.query.get_or_404(id)
    db.session.delete(contact)
    db.session.commit()
    flash('Contact deleted successfully!', 'success')
    return redirect(url_for('contacts'))

@app.route('/send_wish/<int:id>', methods=['GET', 'POST'])
def send_wish(id):
    contact = Contact.query.get_or_404(id)
    
    if request.method == 'POST':
        message = request.form.get('message')
        gif_url = request.form.get('gif_url')
        
        # Update custom message if provided
        if message:
            contact.custom_message = message
            db.session.commit()
        
        # Send email
        success = send_birthday_email(contact, gif_url)
        
        if success:
            flash('Birthday wish sent successfully!', 'success')
        else:
            flash('Failed to send birthday wish. Please check your email settings.', 'danger')
        
        return redirect(url_for('contacts'))
    
    # Get random wish and GIF for preview
    random_wish = get_random_wish()
    random_gif = get_random_gif()
    
    return render_template('send_wish.html', contact=contact, random_wish=random_wish, random_gif=random_gif, app_name="YoHoo")

@app.route('/wishes')
def wishes():
    all_wishes = BirthdayWish.query.all()
    return render_template('wishes.html', wishes=all_wishes, app_name="YoHoo")

@app.route('/add_wish', methods=['GET', 'POST'])
def add_wish():
    if request.method == 'POST':
        message = request.form.get('message')
        category = request.form.get('category')
        
        new_wish = BirthdayWish(message=message, category=category)
        db.session.add(new_wish)
        db.session.commit()
        
        flash('Birthday wish added successfully!', 'success')
        return redirect(url_for('wishes'))
    
    return render_template('add_wish.html', app_name="YoHoo")

@app.route('/gifs')
def gifs():
    all_gifs = GifCollection.query.all()
    return render_template('gifs.html', gifs=all_gifs, app_name="YoHoo")

@app.route('/add_gif', methods=['GET', 'POST'])
def add_gif():
    if request.method == 'POST':
        url = request.form.get('url')
        category = request.form.get('category')
        
        new_gif = GifCollection(url=url, category=category, is_custom=True)
        db.session.add(new_gif)
        db.session.commit()
        
        flash('GIF added successfully!', 'success')
        return redirect(url_for('gifs'))
    
    return render_template('add_gif.html', app_name="YoHoo")

@app.route('/settings')
def settings():
    return render_template('settings.html', app_name="YoHoo")

@app.route('/change_theme', methods=['POST'])
def change_theme():
    theme = request.form.get('theme')
    session['theme'] = theme
    return redirect(url_for('settings'))

@app.route('/random_wish')
def random_wish():
    category = request.args.get('category')
    wish = get_random_wish(category)
    return {'message': wish}

@app.route('/random_gif')
def random_gif():
    category = request.args.get('category')
    gif = get_random_gif(category)
    return {'url': gif}

# Initialize database with sample data
@app.before_first_request
def initialize_db():
    db.create_all()
    
    # Add sample wishes if none exist
    if BirthdayWish.query.count() == 0:
        sample_wishes = [
            BirthdayWish(message="Happy Birthday! May your day be filled with joy and laughter!", category="general"),
            BirthdayWish(message="Wishing you a fantastic birthday filled with love and happiness!", category="general"),
            BirthdayWish(message="Another year older, another year wiser. Happy Birthday!", category="funny"),
            BirthdayWish(message="May your birthday be as amazing as you are!", category="heartfelt"),
            BirthdayWish(message="Sending you warm wishes on your special day!", category="general")
        ]
        db.session.add_all(sample_wishes)
    
    # Add sample GIFs if none exist
    if GifCollection.query.count() == 0:
        sample_gifs = [
            GifCollection(url="https://media.giphy.com/media/3ohs4BSacFKI7A717y/giphy.gif", category="general"),
            GifCollection(url="https://media.giphy.com/media/l4KibWpBGWchSqCRy/giphy.gif", category="funny"),
            GifCollection(url="https://media.giphy.com/media/26FPpSuhgHvYo9Kyk/giphy.gif", category="heartfelt"),
            GifCollection(url="https://media.giphy.com/media/26BRtW4zppWWjrsPu/giphy.gif", category="general"),
            GifCollection(url="https://media.giphy.com/media/3o6gDWzmAzrpi5DQU8/giphy.gif", category="funny")
        ]
        db.session.add_all(sample_gifs)
    
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True) 