from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv(".env.local")

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)

    from app.routes import auth, dashboard, scraper

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(scraper.bp)

    return app
