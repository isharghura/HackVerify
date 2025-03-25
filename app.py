from flask import (
    Flask,
    redirect,
    request,
    send_from_directory,
    render_template,
    session,
)
import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv(".env.local")

app = Flask(__name__)

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# linkedin oauth
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

# secret key for flask app
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# server static files
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# serve index.htm
@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


# linkedin oauth routes
@app.route("/auth/linkedin")
def linkedin_auth():
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={LINKEDIN_CLIENT_ID}&"
        f"redirect_uri={LINKEDIN_REDIRECT_URI}&"
        f"scope=openid%20profile%20email&"
        f"state=anti_csrf_token"
    )
    return redirect(auth_url)


@app.route("/auth/linkedin/callback")
def linkedin_callback():
    try:
        code = request.args.get("code")
        token_response = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        token_data = token_response.json()
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        expires_at = datetime.now() + timedelta(seconds=expires_in)

        if "error" in token_data:
            return f"LinkedIn token error: {token_data['error_description']}", 400

        access_token = token_data["access_token"]

        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        profile_data = profile_response.json()

        if "error" in profile_data:
            return f"LinkedIn API error: {profile_data['message']}", 400

        user_data = {
            "email": profile_data.get("email", ""),
            "linkedin_id": profile_data["sub"],
            "full_name": profile_data.get("name", ""),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
        }

        supabase.table("users").upsert(
            user_data,
            on_conflict="linkedin_id",  # update if linkedin_id exists
        ).execute()

        # set up a session
        session["user_email"] = profile_data.get("email")
        session["access_token"] = access_token
        session.permanent = True

        return redirect("/dashboard")

    except Exception as e:
        print("Error:", str(e))
        return "Authentication failed", 500


# dashboard route
@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect("/auth/linkedin")

    response = (
        supabase.table("users").select("*").eq("email", session["user_email"]).execute()
    )

    if not response.data:
        return "User not found", 404

    user_data = response.data[0]
    return render_template("dashboard.html", user=user_data)


@app.route("/check-auth")
def check_auth():
    try:
        # is user in a session
        if "user_email" not in session:
            return {"status": "unauthenticated"}, 401

        # retrieve user
        user_data = (
            supabase.table("users")
            .select("*")
            .eq("email", session["user_email"])
            .execute()
            .data
        )

        if not user_data:
            return {"status": "unauthenticated"}, 401

        user = user_data[0]

        # does token need refreshing?
        if datetime.now() > datetime.fromisoformat(user["expires_at"]):
            try:
                token_response = requests.post(
                    "https://www.linkedin.com/oauth/v2/accessToken",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": user["refresh_token"],
                        "client_id": LINKEDIN_CLIENT_ID,
                        "client_secret": LINKEDIN_CLIENT_SECRET,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_data = token_response.json()

                if "error" in token_data:
                    return {"status": "token_refresh_failed"}, 401

                # update user tokens in db
                expires_at = datetime.now() + timedelta(
                    seconds=token_data["expires_in"]
                )
                supabase.table("users").update(
                    {
                        "access_token": token_data["access_token"],
                        "expires_at": expires_at.isoformat(),
                    }
                ).eq("email", session["user_email"]).execute()

                # update session with new token
                session["access_token"] = token_data["access_token"]

            except Exception as e:
                app.logger.error(f"Token refresh failed: {str(e)}")
                return {"status": "token_refresh_failed"}, 401

        return {
            "status": "authenticated",
            "user": {
                "email": user["email"],
                "name": user["full_name"],
                "linkedin_id": user["linkedin_id"],
            },
        }, 200

    except Exception as e:
        app.logger.error(f"Auth check failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


# handle form submissions
@app.route("/api/submissions", methods=["POST"])
def submissions():
    # is user logged in
    if "user_email" not in session:
        return {"error": "Unauthorized"}, 401

    try:
        user_data = (
            supabase.table("users")
            .select("email, linkedin_id, full_name")
            .eq("email", session["user_email"])
            .execute()
            .data
        )

        if not user_data:
            return {"error": "User not found"}, 404

        user = user_data[0]
        data = request.get_json()
        devpost = data.get("devpost")

        if not devpost:
            return {"error": "Devpost link is required"}, 400

        response = (
            supabase.table("interested_organizers")
            .insert(
                {
                    "linkedin": f"https://www.linkedin.com/in/{user['linkedin_id']}",
                    "devpost": devpost,
                    "email": user["email"],
                    "name": user["full_name"],
                }
            )
            .execute()
        )

        return {"message": "Submission successful!"}, 200

    except Exception as e:
        app.logger.error(f"Submission error: {str(e)}")
        return {"error": "Internal server error"}, 500


# run flask app
if __name__ == "__main__":
    app.run(port=8000)
