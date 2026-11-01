# Secure Authentication Lab

A beginner-friendly authentication service built with Python and Flask. This project demonstrates essential authentication security practices, including password hashing, input validation, rate limiting, session management, and logout functionality.

## Features

- **User Registration:** Creates user accounts after validating usernames and passwords.
- **Password Hashing:** Stores password hashes instead of plain-text passwords using Werkzeug's password-hashing functions.
- **Input Validation:** Checks username and password requirements on the server.
- **Login Authentication:** Verifies submitted credentials against stored password hashes.
- **Rate Limiting:** Limits registration and login requests to five requests per minute per client IP address.
- **Secure Session Cookies:** Configures HttpOnly and SameSite cookie attributes.
- **Protected Profile:** Requires authentication to access the `/me` endpoint.
- **Logout:** Clears the current session.
- **Session Expiry:** Configures a 15-minute permanent-session lifetime.
- **Automated Tests:** Includes tests for successful operations and common invalid requests.

## Technologies Used

- Python
- Flask
- Flask-Limiter
- Flask-SQLAlchemy
- SQLite
- Werkzeug
- pytest

## Project Structure

```text
secure-authentication-lab/
├── app.py
├── test_auth.py
├── requirements.txt
├── README.md
├── test-results.png
└── .gitignore
```

The `test-results.png` file is optional evidence of the successful test run. The `.venv` folder and local database should not be committed to the repository.

## Requirements

- Python 3.10 or later
- pip
- A terminal or command prompt

## Installation

### 1. Clone the repository

After publishing this project to GitHub, clone it using:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd secure-authentication-lab
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with your actual repository URL.

### 2. Create a virtual environment

On Windows:

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## Running the Application

Start the application:

```powershell
python app.py
```

By default, the local development server runs at:

```text
http://127.0.0.1:5000
```

Open this address in a browser to check whether the service is running.

Stop the server with `Ctrl + C`.

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Returns service information |
| `/register` | POST | Registers a new user |
| `/login` | POST | Authenticates a user |
| `/me` | GET | Returns the authenticated user's profile |
| `/logout` | POST | Clears the current session |

### Example: Register a user

Send a POST request to `/register` with a JSON body:

```json
{
  "username": "student123",
  "password": "StrongPassword123!"
}
```

The username must contain 3–30 alphanumeric characters, and the password must contain 12–128 characters.

### Example: Log in

Send a POST request to `/login` with the same username and password.

A successful login creates an authenticated session.

### Example: Access the profile

Send a GET request to `/me` using the same client or session that logged in.

Unauthenticated requests receive an HTTP 401 response.

### Example: Log out

Send a POST request to `/logout` to clear the session.

## Running the Tests

Activate the virtual environment, then run:

```powershell
python -m pytest -v
```

### Test Results

The current test run completed successfully:

**13 passed in 3.29 seconds.**

The tests cover registration, duplicate accounts, password hashing, successful and unsuccessful login, profile access, logout, input validation, invalid JSON, and login rate limiting.

## Authentication Security Note

### 1. Password Storage

Passwords are hashed with Werkzeug rather than stored as plain text. During login, the submitted password is checked against the stored hash.

### 2. Input Validation

The server validates registration input before creating an account. Invalid usernames, short passwords, and malformed JSON requests are rejected.

### 3. Rate Limiting

Registration and login endpoints are limited to five requests per minute per client IP address. This helps reduce repeated automated attempts.

### 4. Session Security

The application configures session cookies with the `HttpOnly` and `SameSite=Lax` attributes. Permanent sessions have a configured lifetime of 15 minutes.

The `Secure` cookie attribute can be enabled by setting `COOKIE_SECURE=true` when serving the application over HTTPS.

### 5. Error Handling

Login failures use a generic error message rather than revealing whether a username exists.

### 6. Limitations and Production Recommendations

This is a learning project, not a production-ready authentication system.

- The application generates a random secret key if `SECRET_KEY` is not configured. Because sessions depend on this key, configure a stable, securely stored secret key before deployment.
- The rate limiter uses in-memory storage, which is not suitable for coordinated rate limiting across multiple production workers.
- Production deployment should use HTTPS and a production WSGI server.
- Browser-based state-changing endpoints may need additional CSRF protection.
- Authentication systems require further security testing before real user data is handled.

## Learning Outcomes

This project demonstrates practical concepts in:

- Secure password storage
- Authentication and session management
- Server-side input validation
- Rate limiting
- REST-style API endpoints
- Automated testing with pytest
- Basic application security documentation

## Disclaimer

This project is intended for educational purposes and local testing. It has not been independently audited for production security.