import os
import secrets
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

# Use a persistent secret key from the environment when available.
# A random key is generated for local development otherwise.
app.config["SECRET_KEY"] = (
    os.environ.get("SECRET_KEY") or secrets.token_hex(32)
)

# SQLite database configuration.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///auth.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session security settings.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
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
    """Store registered users and their password hashes."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


# --------------------------------------------------
# Input Validation
# --------------------------------------------------

def valid_credentials(username, password):
    """Validate username and password during registration."""

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
    """Display basic information about the authentication service."""

    return jsonify({
        "message": "Secure Authentication Lab is running.",
        "endpoints": ["/register", "/login", "/me", "/logout"],
    }), 200


# --------------------------------------------------
# User Registration
# --------------------------------------------------

@app.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    """Register a user after validating and hashing the password."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request."}), 400

    username = data.get("username")
    password = data.get("password")

    if not valid_credentials(username, password):
        return jsonify({
            "error": (
                "Username must be 3-30 alphanumeric characters "
                "and password must be 12-128 characters."
            )
        }), 400

    existing_user = User.query.filter_by(username=username).first()

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

    return jsonify({
        "message": "Account created successfully."
    }), 201


# --------------------------------------------------
# User Login
# --------------------------------------------------

@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    """Verify credentials and create an authenticated session."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid username or password."
        }), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "error": "Invalid username or password."
        }), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not check_password_hash(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid username or password."
        }), 401

    # Clear old session data before creating a new authenticated session.
    session.clear()
    session.permanent = True
    session["user_id"] = user.id

    return jsonify({
        "message": "Login successful."
    }), 200


# --------------------------------------------------
# Protected Profile Route
# --------------------------------------------------

@app.route("/me", methods=["GET"])
def me():
    """Return the current user's profile only when authenticated."""

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
# User Logout
# --------------------------------------------------

@app.route("/logout", methods=["POST"])
def logout():
    """Clear the current session to log the user out."""

    session.clear()

    return jsonify({
        "message": "Logged out successfully."
    }), 200


# --------------------------------------------------
# Rate Limit Error Handler
# --------------------------------------------------

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Return a clear message when a rate limit is exceeded."""

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