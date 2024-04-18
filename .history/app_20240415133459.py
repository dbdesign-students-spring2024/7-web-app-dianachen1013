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

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database

    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live


# set up the routes
@app.route('/upload', methods=['GET', 'POST'])
def upload_clothing():
    if request.method == 'POST':
        clothing_data = {
            "title": request.form['title'],
            "description": request.form['description'],
            "size": request.form['size'],
            "condition": request.form['condition'],
            "image_url": request.form['image_url'],  # Assuming users provide a URL to an image
        }
        mongo.db.clothes.insert_one(clothing_data)
        return redirect(url_for('list_clothing'))
    return render_template('upload_clothing.html')

@app.route('/')
def list_clothing():
    clothes = mongo.db.clothes.find()
    return render_template('list_clothing.html', clothes=clothes)

@app.route('/clothing/<id>')
def clothing_detail(id):
    clothing_item = mongo.db.clothes.find_one({'_id': ObjectId(id)})
    return render_template('clothing_detail.html', item=clothing_item)


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run(load_dotenv=True)
