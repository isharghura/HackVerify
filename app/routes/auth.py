from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from flask import Blueprint, current_app, jsonify, redirect, session, request
import requests
from supabase import create_client

bp = Blueprint("auth", __name__)

load_dotenv(".env.local")

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# linkedin oauth
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

# linkedin oauth routes
@bp.route("/auth/linkedin")
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


@bp.route("/auth/linkedin/callback")
def linkedin_callback():
    try:
        code = request.args.get("code")
        if not code:
            return "missing auth code", 400

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
        if "error" in token_data:
            current_app.logger.error(f"token error: {token_data}")
            return f"LinkedIn token error: {token_data.get('error_description')}", 400

        access_token = token_data["access_token"]

        if "error" in token_data:
            return f"LinkedIn token error: {token_data['error_description']}", 400

        profile_response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        profile_data = profile_response.json()

        if "error" in profile_data:
            current_app.logger.error(f"profile error: {profile_data}")
            return f"LinkedIn API error: {profile_data['message']}", 400

        user_data = {
            "email": profile_data.get("email", ""),
            "linkedin_id": profile_data["sub"],
            "full_name": profile_data.get("name", ""),
            "access_token": access_token,
            "picture": profile_data.get("picture"),
        }

        response = (
            supabase.table("users")
            .upsert(
                user_data,
                on_conflict="linkedin_id",  # update if linkedin_id exists
            )
            .execute()
        )

        # set up a session
        session.clear()
        session["linkedin_id"] = profile_data.get("sub")
        session["access_token"] = access_token
        session.permanent = True

        return redirect("/dashboard")

    except Exception as e:
        print("callback error:", str(e))
        return "Authentication failed", 500

# is user authenticated
@bp.route("/check-auth")
def check_auth():
    try:
        # is user in a session
        if "linkedin_id" not in session:
            return redirect("/auth/linkedin")

        # retrieve user
        user_data = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
            .data
        )

        if not user_data:
            return {"status": "unauthenticated"}, 401

        user = user_data[0]

        # does token need refreshing?
        if datetime.now() > datetime.fromisoformat(user["expires_at"]) - timedelta(
            minutes=5
        ):
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
                supabase.table("users").update(
                    {
                        "access_token": token_data["access_token"],
                    }
                ).eq("linkedin_id", session["linkedin_id"]).execute()

                # update session with new token
                session["access_token"] = token_data["access_token"]

            except Exception as e:
                pass

        return {
            "status": "authenticated",
            "user": {
                "email": user["email"],
                "name": user["full_name"],
                "linkedin_id": user["linkedin_id"],
            },
        }, 200

    except Exception as e:
        current_app.logger.error(f"auth check failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200
