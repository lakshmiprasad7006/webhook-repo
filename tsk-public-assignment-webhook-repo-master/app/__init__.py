from flask import Flask

from app.webhook.routes import webhook


# Creating our flask app
def create_app():
    app = Flask(__name__)
    # Home page route at root
    @app.route('/')
    def home():
        return '<h1>Welcome to the GitHub Webhook Dashboard</h1><p>Use /webhook/ui to view events.</p>'
    # registering all the blueprints
    app.register_blueprint(webhook)
    return app