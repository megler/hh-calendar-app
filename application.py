import os
import sqlite3
import functools
import uuid
import tinify
import stripe
import pymysql
import pymysql.cursors
from flask import Flask, session, current_app, g, render_template, request, redirect, send_file, g, url_for
from flask_session import Session
from tempfile import mkdtemp
from datetime import timedelta
from flask.cli import with_appcontext
from os.path import join, dirname, realpath
from werkzeug.utils import secure_filename
from contextlib import closing

application = app = Flask(__name__)

SECRET_KEY=os.urandom(24)

stripe_keys = {
  'secret_key': os.environ['STRIPE_SECRET_KEY'],
  'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY']
}

stripe.api_key = stripe_keys['secret_key']
tinify.key = os.environ['TINIFY_SECRET_KEY']

# Sessions

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=120)
Session(app)

# Database

connection = pymysql.connect(host=os.getenv("RDS_HOSTNAME"),
                             user=os.getenv("RDS_USERNAME"),
                             port=int(os.getenv("RDS_PORT")),
                             password=os.getenv("RDS_PASSWORD"),
                             db=os.getenv("RDS_DB_NAME"),
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor
                            )
try:
    with connection.cursor() as cursor:
        cursor.execute("SET sql_notes = 0")
        sqlQuery =  "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTO_INCREMENT NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL, email TEXT NOT NULL, uid TEXT NOT NULL )"
        cursor.execute(sqlQuery)
        sqlQuery =  "CREATE TABLE IF NOT EXISTS dogs (id INTEGER PRIMARY KEY AUTO_INCREMENT, user_id TEXT NOT NULL, dog_names TEXT NOT NULL, url TEXT NOT NULL, url_thumb text NOT NULL )"
        cursor.execute(sqlQuery)
        sqlQuery =  "CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY AUTO_INCREMENT, user_id TEXT NOT NULL, dog_names TEXT NOT NULL, votes INTEGER, entry INTEGER)"
        cursor.execute(sqlQuery)
finally:
    connection.commit()
    cursor.close()


# Routes
@app.route('/')
def index():
    session['uid'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route("/submit")
def storage():
    if session.get('uid') != True:
        session['uid'] = str(uuid.uuid4())
    # If user has not paid to enter their dog, redirect to the checkout
    if session.get('paid') != True:
        return redirect('/calendar_entry')
    else:
        return render_template('submit.html')

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Get form submision data to insert in database

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        dog_names = request.form.get("dog_names")
        uid = session['uid']

        image_file = request.files['file']
        filename = secure_filename(image_file.filename)  # This is convenient to validate your filename, otherwise just use file.filename

        # Store image on S3
        source = tinify.from_file(image_file)
        source.store(
            service="s3",
            aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            region="us-east-1",
            path=f"calendar-photos/{filename}"
        )

        # Resize to Thumbnail
        resized = source.resize(
            method="scale",
            width=250
        )

        # Rename thumbnail image and upload to S3
        name, ext = os.path.splitext(filename)
        new_name = "{name}_{thumb}{ext}".format(name=name, thumb="thumb", ext=ext)
        resized.store(
            service="s3",
            aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            region="us-east-1",
            path=f"calendar-photos/{new_name}"
        )
		
		# insert to database
        new_name_url = str(new_name)
        votes = 0
        entry = 10
        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "INSERT INTO customers (first_name, last_name, email, uid) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (first_name, last_name, email, uid))
                connection.commit()
                sql = "INSERT INTO dogs (user_id, dog_names, url, url_thumb) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (uid, dog_names, filename, new_name_url))
                connection.commit()
                sql = "INSERT INTO votes (user_id, dog_names, votes, entry) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (uid, dog_names, votes, entry))
                connection.commit()
                cursor.close()
        finally:
            # Set session to false so user can't return to /submit without paying again.
            session['paid'] = False
            return redirect('/vote')
    else:
        return render_template('submit.html')

@app.route("/vote")
def vote():
    if session.get('uid') != True:
        session['uid'] = str(uuid.uuid4())
    try:
        session['uid'] = str(uuid.uuid4())
        with connection.cursor() as cursor:
            dogs = 'SELECT * FROM dogs INNER JOIN customers ON dogs.user_id=customers.uid INNER JOIN votes ON customers.uid=votes.user_id'
            cursor.execute(dogs)
            image_url = 'https://calendar-photos.s3.amazonaws.com/'
            dog_table = cursor.fetchall()
            cursor.close()
    finally:
        return render_template('vote.html', table=dog_table, image_url=image_url, key=stripe_keys['publishable_key'])

@app.route('/leader')
def leader():
    if session.get('uid') != True:
        session['uid'] = str(uuid.uuid4())
    try:
        session['uid'] = str(uuid.uuid4())
        with connection.cursor() as cursor:
            dogs = 'SELECT * FROM dogs INNER JOIN customers ON dogs.user_id=customers.uid INNER JOIN votes ON customers.uid=votes.user_id ORDER BY votes DESC LIMIT 12'
            cursor.execute(dogs)
            image_url = 'https://calendar-photos.s3.amazonaws.com/'
            leader_table = cursor.fetchall()
            cursor.close()
    finally:
        return render_template('leader.html', table=leader_table, image_url=image_url)

@app.route('/calendar_entry')
def calendar_entry():
    if session.get('uid') != True:
        session['uid'] = str(uuid.uuid4())
    return render_template('calendar_entry.html', key=stripe_keys['publishable_key'])

@app.route('/entry', methods=['POST'])
def entry():
    try:
        amount = 1000   # amount in cents
        customer = stripe.Customer.create(
            email=request.form['stripeEmail'],
            source=request.form['stripeToken']
        )
        stripe.Charge.create(
            customer=customer.id,
            amount=amount,
            currency='usd',
            description='Houndhaven Calendar Entry'
        )
        session['paid'] = True
        return render_template('submit.html')
    except stripe.error.StripeError:
        return render_template('error.html')

@app.route('/create_votes', methods=['POST', 'GET'])
def create_votes():
    quantity = request.form['quantity']
    if quantity == "":
        return "You Need To Enter An Amount In Order To Vote"
    else:
        session['dog_names'] = request.form['dog_name']
        session['last_name'] = request.form['last_name']
        session['new_votes'] = request.form['quantity']
        session['amount'] = int(session['new_votes']) * 100
        return redirect('/checkout')

@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    dog_names = session['dog_names']
    last_name = session['last_name']
    new_votes = int(session['new_votes'])
    amount = session['amount']
    return render_template('checkout.html', dog_names=dog_names, new_votes=new_votes, amount=amount, last_name=last_name, key=stripe_keys['publishable_key'])

@app.route('/finish', methods=['POST', 'GET'])
def finish():
    dog_names = session['dog_names']
    new_votes = int(session['new_votes'])
    try:
        with connection.cursor() as cursor:
            cursor.execute ("""UPDATE votes SET votes = votes + %s WHERE dog_names = %s""", (new_votes, dog_names))
            connection.commit()
            cursor.close()
            return redirect('/vote')
    finally:
        return redirect('/vote')


if __name__ == "__main__":
    app.run()