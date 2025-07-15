from flask_pymongo import PyMongo

from flask import Flask

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/database"
# Setup MongoDB here
mongo = PyMongo(app)
collections = mongo.db.users    