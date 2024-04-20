# -*- coding: utf-8 -*-
"""
Created on Mon Apr 15 13:32:25 2024

@author: 86136
"""


#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime

from flask import Flask, render_template, request, redirect, url_for, make_response


# import logging
import sentry_sdk
from sentry_sdk.integrations.flask import (
    FlaskIntegration,
)  # delete this if not using sentry.io

# flask login
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient

# from markupsafe import escape
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from dotenv import load_dotenv

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
load_dotenv(override=True)  # take environment variables from .env.

# initialize Sentry for help debugging... this requires an account on sentrio.io
# you will need to set the SENTRY_DSN environment variable to the value provided by Sentry
# delete this if not using sentry.io
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    # enable_tracing=True,
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    # We recommend adjusting this value in production.
    
    integrations=[FlaskIntegration()],
    send_default_pii=True,
)

# instantiate the app using sentry for debugging
app = Flask(__name__)
# # turn on debugging if in development mode
# app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database
    users_collection = db['users']
    clothes_collection = db['clothes']
    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live



@login_manager.user_loader
def load_user(user_id):
    user = db.users.find_one({"_id": user_id})
    if not user:
        return None
    return User(user)

# User class
class User(UserMixin):
    def __init__(self, user_json):
        self.id = str(user_json["_id"])
        self.username = user_json["username"]

# Routes for login and logout
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.users.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            user_obj = User(user)
            login_user(user_obj)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/create_account', methods=['POST'])
def create_account():
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']  # Ensure you're capturing email in your form
    # Check if user already exists
    existing_user = db.users.find_one({"username": username})
    if existing_user:
        return render_template('login.html', error='Username already exists')
    
    hashed_password = generate_password_hash(password)
    # Insert the new user into the database
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "email": email
    })
    # Optionally log the user in right after creating an account, or redirect to login page
    new_user = users_collection.find_one({"username": username})
    
    user_obj(User(new_user))
    login_user(user_obj)
    return redirect(url_for('home'))


# set up the routes
@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    return render_template("index.html")


@app.route("/read")
def read():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    docs = db.exampleapp.find({}).sort(
        "created_at", -1
    )  # sort in descending order of created_at timestamp
    return render_template("read.html", docs=docs)  # render the read template


@app.route("/create")
def create():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    return render_template("create.html")  # render the create template


@app.route("/create", methods=["POST"])
def create_post():
    """
    Route for POST requests to the create page.
    Accepts the form submission data for a new document and saves the document to the database.
    """
    name = request.form["fname"]
    message = request.form["fmessage"]
    brand = request.form["fbrand"]
    type_of_clothes = request.form["ftype"]
    size = request.form["fsize"]
    condition = request.form["fcondition"]
    image_url = request.form["fimage_url"]


    # create a new document with the data the user entered
    doc = {"user_id": current_user.get_id(),"name": name, "message": message, "brand": brand, "type_of_clothes": type_of_clothes, "size": size, "condition": condition, "image_url": image_url,"created_at": datetime.datetime.utcnow()}
    db.exampleapp.insert_one(doc)  # insert a new document


    return redirect(
        url_for("read")
    )  # tell the browser to make a request for the /read route


@app.route("/edit/<mongoid>")
def edit(mongoid):
    """
    Route for GET requests to the edit page.
    Displays a form users can fill out to edit an existing record.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """
    doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    return render_template(
        "edit.html", mongoid=mongoid, doc=doc
    )  # render the edit template


@app.route("/edit/<mongoid>", methods=["POST"])
def edit_post(mongoid):
    """
    Route for POST requests to the edit page.
    Accepts the form submission data for the specified document and updates the document in the database.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """
    
    name = request.form["fname"]
    message = request.form["fmessage"]
    brand = request.form["fbrand"]
    type_of_clothes = request.form["ftype"]
    size = request.form["fsize"]
    condition = request.form["fcondition"]
    image_url = request.form["fimage_url"]


    if doc and doc["user_id"] == current_user.id:
      doc = {
          # "_id": ObjectId(mongoid),
          "name": name,
          "message": message,
          "brand": brand,
          "type_of_clothes": type_of_clothes,
          "size": size,
          "condition": condition,
          "image_url": image_url,
          "created_at": datetime.datetime.utcnow(),
      }
    else:
        return "Unauthorized", 403

    db.exampleapp.update_one(
        {"_id": ObjectId(mongoid)}, {"$set": doc}  # match criteria
    )

    return redirect(
        url_for("read")
    )  # tell the browser to make a request for the /read route


@app.route("/delete/<mongoid>")
def delete(mongoid):
    """
    Route for GET requests to the delete page.
    Deletes the specified record from the database, and then redirects the browser to the read page.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be deleted.
    """
    
    if doc["user_id"] == current_user.id:
        db.exampleapp.delete_one({"_id": ObjectId(mongoid)})
        return redirect(
        url_for("read")
    )  # tell the web browser to make a request for the /read route.
    else:
        return "Unauthorized", 403
    


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response(f"output: {pull_output}", 200)
    response.mimetype = "text/plain"
    return response


@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run(load_dotenv=True)
