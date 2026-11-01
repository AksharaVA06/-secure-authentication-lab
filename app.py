
import os
import secrets
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, request, jsonify, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# --------------------------------------------------
# Application Configuration
# --------------------------------------------------

app = Flask(__name__)

APP_ENV = os.environ.get("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"


# --------------------------------------------------
# Security Logging Configuration
# --------------------------------------------------

security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)
security_logger.propagate = False

if not security_logger.handlers:
    handler = RotatingFileHandler(
        "security.log",
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    security_logger.addHandler(handler)


# --------------------------------------------------
# Secret Key Configuration
# --------------------------------------------------

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY must be configured in production."
        )

    SECRET_KEY = secrets.token_hex(32)

app.config["SECRET_KEY"] = SECRET_KEY


# --------------------------------------------------
# Database Configuration
# --------------------------------------------------

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///auth.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# --------------------------------------------------
# Session Security
# --------------------------------------------------

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_COOKIE_SECURE"] = (
    IS_PRODUCTION
    or os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=15)


# --------------------------------------------------
# Database and Rate Limiter
# --------------------------------------------------

db = SQLAlchemy(app)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


# --------------------------------------------------
# User Database Model
# --------------------------------------------------

class User(db.Model):
    """Store registered users and password hashes."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


# --------------------------------------------------
# Input Validation
# --------------------------------------------------

def valid_credentials(username, password):
    return (
        isinstance(username, str)
        and isinstance(password, str)
        and 3 <= len(username) <= 30
        and username.isalnum()
        and 12 <= len(password) <= 128
    )


# --------------------------------------------------
# Home Route
# --------------------------------------------------

@app.route("/")
def home():
    return jsonify({
        "message": "Secure Authentication Lab is running.",
        "endpoints": ["/register", "/login", "/me", "/logout"],
    }), 200


# --------------------------------------------------
# Registration
# --------------------------------------------------

@app.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid request."
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not valid_credentials(username, password):
        return jsonify({
            "error": (
                "Username must be 3-30 alphanumeric characters "
                "and password must be 12-128 characters."
            )
        }), 400

    existing_user = User.query.filter_by(
        username=username
    ).first()

    if existing_user:
        return jsonify({
            "error": "Unable to create account."
        }), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
    )

    db.session.add(user)
    db.session.commit()

    security_logger.info("EVENT=REGISTRATION_SUCCESS")

    return jsonify({
        "message": "Account created successfully."
    }), 201


# --------------------------------------------------
# Login
# --------------------------------------------------

@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        security_logger.warning("EVENT=LOGIN_INVALID_REQUEST")

        return jsonify({
            "error": "Invalid username or password."
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        security_logger.warning("EVENT=LOGIN_INVALID_REQUEST")

        return jsonify({
            "error": "Invalid username or password."
        }), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not check_password_hash(
        user.password_hash, password
    ):
        security_logger.warning("EVENT=LOGIN_FAILURE")

        return jsonify({
            "error": "Invalid username or password."
        }), 401

    session.clear()
    session.permanent = True
    session["user_id"] = user.id

    security_logger.info("EVENT=LOGIN_SUCCESS")

    return jsonify({
        "message": "Login successful."
    }), 200


# --------------------------------------------------
# Protected Profile
# --------------------------------------------------

@app.route("/me", methods=["GET"])
def me():

    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "error": "Authentication required."
        }), 401

    user = db.session.get(User, user_id)

    if user is None:
        session.clear()

        return jsonify({
            "error": "Authentication required."
        }), 401

    return jsonify({
        "username": user.username
    }), 200


# --------------------------------------------------
# Logout
# --------------------------------------------------

@app.route("/logout", methods=["POST"])
def logout():

    if session.get("user_id") is not None:
        security_logger.info("EVENT=LOGOUT")

    session.clear()

    return jsonify({
        "message": "Logged out successfully."
    }), 200


# --------------------------------------------------
# Rate Limit Error Handler
# --------------------------------------------------

@app.errorhandler(429)
def rate_limit_exceeded(error):

    security_logger.warning("EVENT=RATE_LIMIT_EXCEEDED")

    return jsonify({
        "error": "Too many requests. Please try again later."
    }), 429


# --------------------------------------------------
# Database Initialization
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# Start Application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False)
