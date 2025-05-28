import re
from bs4 import BeautifulSoup
from flask import (
    Flask,
    json,
    jsonify,
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
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urljoin
import time

load_dotenv(".env.local")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)

# supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# linkedin oauth
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

# github api token
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN")


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
            app.logger.error(f"token error: {token_data}")
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
            app.logger.error(f"profile error: {profile_data}")
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


# dashboard route
@app.route("/dashboard")
def dashboard():
    if "linkedin_id" not in session:
        return redirect("/auth/linkedin")
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
        )

        if not response.data:
            return redirect("/auth/linkedin")

        return render_template("dashboard.html", user=response.data[0])

    except Exception as e:
        app.logger.error(f"dashboard error: {str(e)}")
        return redirect("/")


@app.route("/check-auth")
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
        app.logger.error(f"auth check failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 500


# handle form submissions
@app.route("/api/submissions", methods=["POST"])
def submissions():
    # is user logged in?
    if "linkedin_id" not in session:
        refresh_response = check_auth()
        if refresh_response.status_code != 200:
            return redirect("/auth/linkedin")

    client_id = session.get("linkedin_id")
    current_time = datetime.now(timezone.utc)

    # get last request
    rate_check = (
        supabase.table("rate_limits")
        .select("created_at")
        .eq("client_id", client_id)
        .eq("endpoint", "submissions")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    # was there actually a request made before?
    if rate_check.data and len(rate_check.data) > 0:
        last_request_time = datetime.fromisoformat(
            rate_check.data[0]["created_at"]
        ).replace(tzinfo=timezone.utc)
        if current_time - last_request_time < timedelta(minutes=5):
            return (
                jsonify(
                    {
                        "error": "rate limit exceeded",
                        "message": "only 1 submission allowed every 5 minutes",
                    }
                ),
                429,
            )

    # update submission time
    supabase.table("rate_limits").upsert(
        {
            "client_id": client_id,
            "endpoint": "submissions",
            "created_at": current_time.isoformat(),
        },
        on_conflict="client_id,endpoint",
    ).execute()

    try:
        # is it json?
        if not request.is_json:
            return jsonify({"error": "request must be JSON"}), 400

        data = request.get_json()
        if "devpost" not in data:
            return jsonify({"error": "devpost link is required"}), 400
        if "website" not in data:
            return jsonify({"error": "hackathon website link is required"}), 400

        user_response = (
            supabase.table("users")
            .select("*")
            .eq("linkedin_id", session["linkedin_id"])
            .execute()
        )

        if not user_response.data:
            return jsonify({"error": "user not found"}), 404

        user = user_response.data[0]

        existing_submission = (
            supabase.table("interested_organizers")
            .select("*")
            .eq("linkedin_id", user["linkedin_id"])
            .eq("devpost", data["devpost"])
            .execute()
        )

        submission_data = {
            "devpost": data["devpost"],
            "website": data["website"],
            "email": user["email"],
            "linkedin_id": user["linkedin_id"],
            "name": user.get("full_name", ""),
        }

        if existing_submission.data and len(existing_submission.data) > 0:
            existing_id = existing_submission.data[0]["id"]
            response = (
                supabase.table("interested_organizers")
                .update(submission_data)
                .eq("id", existing_id)
                .execute()
            )
        else:
            submission_data["created_at"] = current_time.isoformat()
            response = (
                supabase.table("interested_organizers")
                .insert(submission_data)
                .execute()
            )

        # was insertion successful?
        if hasattr(response, "error") and response.error:
            app.logger.error(f"Supabase error: {response.error}")
            return (
                jsonify({"error": "Database error", "details": str(response.error)}),
                500,
            )

        return jsonify({"message": "submission successful!"}), 200

    except Exception as e:
        app.logger.error(f"submission error: {str(e)}", exc_info=True)
        return jsonify({"error": "internal server error", "details": str(e)}), 500


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# web scraper to find all projects from devpost link
@app.route("/scrape_devpost_link", methods=["POST"])
def scrape_devpost_link(devpost_link: str):
    all_project_links = []
    page = 1

    print(f"scraping {devpost_link}")

    # look for hackathon period first
    devpost_dates_url = f"{devpost_link}/details/dates"
    dates = []
    print(f"scraping {devpost_dates_url} for when hackathon begins and ends")

    try:
        response = requests.get(devpost_dates_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        date_tags = soup.find_all(
            "td", attrs={"data-iso-date": True}, class_=lambda x: x != "active"
        )

        for tag in date_tags:
            iso_date = tag["data-iso-date"]
            dates.append(iso_date)

        for i in range(len(dates)):
            print(f"{dates[i]}\n")

    except Exception as e:
        print(f"error scraping webpage: {str(e)}")

    while True:
        gallery_url = f"{devpost_link}/project-gallery?page={page}"
        print(f"scraping page {page}: {gallery_url}")

        try:
            response = requests.get(gallery_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # all project link tags in html
            project_anchors = soup.select('a.block-wrapper-link[href*="/software/"]')
            page_links = [a["href"] for a in project_anchors]

            if not page_links:
                print("no more projects found")
                break

            all_project_links.extend(page_links)
            page += 1

        except Exception as e:
            print(f"error scraping page {page}: {str(e)}")
            break

    print(f"found {len(all_project_links)} total projects")

    # put into supabase
    try:
        supabase.table("devpost_hackathons").upsert(
            {
                "devpost_link": devpost_link,
                "project_links": all_project_links,
                "last_scraped_at": datetime.now(timezone.utc).isoformat(),
                "datesandtimes": dates,
            },
            on_conflict="devpost_link",
        ).execute()
        print("all projects stored successfully")

    except Exception as e:
        print(f"database error: {str(e)}")


def get_github_link(project_link):
    try:
        response = requests.get(project_link)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        print("searching through " + project_link)
        github_link = soup.find("a", href=re.compile(r"github\.com"))
        github_value = github_link["href"] if github_link else "no GitHub link found"
        print(f"found {github_value}")
        return github_value

    except Exception as e:
        print(f"error fetching GitHub link: {e}")
        return "no GitHub link found"


@app.route("/get_all_github_links", methods=["POST"])
def get_all_github_links(devpost_link):
    all_github_links = []
    try:
        # get projs from supabase
        response = (
            supabase.table("devpost_hackathons")
            .select("*")
            .eq("devpost_link", devpost_link)
            .execute()
        )

        if response.data and len(response.data) > 0:
            project_links = response.data[0].get("project_links", "")

            # clean and parse the links
            if isinstance(project_links, str):
                # remove brackets and quotes
                project_links = project_links.strip("[]\"'")
                project_links_list = [
                    link.strip(" \"'")
                    for link in project_links.split(",")
                    if link.strip()
                ]
            elif isinstance(project_links, list):
                project_links_list = project_links
            else:
                project_links_list = []

            # now we can get the githubs
            for project_link in project_links_list:
                if not project_link.startswith(("http://", "https://")):
                    print(f"skipping invalid project link: {project_link}")
                    all_github_links.append("no GitHub link found")
                    continue
                try:
                    github_link = get_github_link(project_link)
                    if github_link:
                        all_github_links.append(github_link)
                except Exception as e:
                    print(f"error fetching GitHub link for {project_link}: {e}")
                    continue
        else:
            print(f"no project links found for {devpost_link}")
            return []

    except Exception as e:
        print(f"error fetching all GitHub links: {e}")
        return None

    try:
        supabase.table("devpost_hackathons").upsert(
            {"devpost_link": devpost_link, "github_links": all_github_links},
            on_conflict="devpost_link",
        ).execute()
        print("all GitHub links stored successfully")
        return all_github_links

    except Exception as e:
        print(f"database error: {str(e)}")
        return None

# in case we're not given base github link
def sanitize_github_url(github_link):
    parsed = urlparse(github_link)
    path_parts = parsed.path.strip('/').split('/')

    # username/github proj name
    if len(path_parts) >= 2:
        base_path = f"/{path_parts[0]}/{path_parts[1]}"
        return f"{parsed.scheme}://{parsed.netloc}{base_path}"
    return github_link


def get_first_last_commit(github_link):
    result = {}
    owner, repo = None, None
    try:
        if not github_link:
            result = {'error': "not a valid github link"}
            return result
        parsed_url = urlparse(github_link)
        path_parts = parsed_url.path.strip("/").split("/")

        if len(path_parts) < 2:
            result = {"error": "not a valid github link"}
            end_time = time.time()
            return result

        owner, repo = path_parts[0], path_parts[1]
        headers = {"Authorization": f"Bearer {GITHUB_API_TOKEN}"}

        commits_api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"

        # get last commit
        last_commit_response = requests.get(
            commits_api_url, headers=headers, params={"per_page": 1}
        )
        last_commit_response.raise_for_status()

        last_commit_data = last_commit_response.json()
        if not last_commit_data:
            result = {"error": f"no commits found for repository {owner}/{repo}."}
            end_time = time.time()
            return result

        last_commit_date = last_commit_data[0]["commit"]["author"]["date"]

        # get first commit
        first_commit_page_response = requests.get(
            commits_api_url, headers=headers, params={"per_page": 100}
        )
        first_commit_page_response.raise_for_status()

        commits_on_current_page = first_commit_page_response.json()
        if not commits_on_current_page:
            result = {
                "error": f"no commits found for {github_link}"
            }
            end_time = time.time()
            return result

        first_commit_date = None

        link_header = first_commit_page_response.headers.get("Link")

        # get to the last page
        if link_header and 'rel="last"' in link_header:
            links = requests.utils.parse_header_links(link_header)
            last_page_url = None
            for link in links:
                if link.get("rel") == "last":
                    last_page_url = link["url"]
                    break

            if last_page_url:
                response_last_page = requests.get(last_page_url, headers=headers)
                response_last_page.raise_for_status()
                commits_on_last_page = response_last_page.json()

                if commits_on_last_page:
                    first_commit_date = commits_on_last_page[-1]["commit"]["author"][
                        "date"
                    ]
                else:
                    # last page is empty, going back to previous page
                    first_commit_date = commits_on_current_page[-1]["commit"]["author"][
                        "date"
                    ]
            else:
                # parsing issue with last page, so going back to previous page
                first_commit_date = commits_on_current_page[-1]["commit"]["author"][
                    "date"
                ]
        else:
            # no 'last' link in headers, it's on the first page then
            first_commit_date = commits_on_current_page[-1]["commit"]["author"]["date"]

        result = {
            "first_commit_date": first_commit_date,
            "last_commit_date": last_commit_date,
        }

    except requests.exceptions.HTTPError as http_err:
        error_message = ""
        if http_err.response.status_code == 404:
            error_message = f"repo {owner}/{repo} not found or not accessible"
        elif http_err.response.status_code == 403:
            error_message = f"cannot access {owner}/{repo}"
        else:
            error_message = f"HTTP error occurred: {http_err} (Status: {http_err.response.status_code})"
        result = {"error": error_message}
    except requests.exceptions.RequestException as req_err:
        result = {"error": f"req error occurred: {req_err}"}
    except KeyError as key_err:
        result = {
            "error": f"unexpected struc, couldn't parse it: {key_err}"
        }
    except Exception as e:
        result = {"error": f"unknwon error: {e}"}
    return result


@app.route("/validate_commits", methods=['POST'])
def check_and_store_commit_validity(devpost_link_to_check: str):
    try:
        # fetch hackathon's data from supabase
        response = (
            supabase.table("devpost_hackathons")
            .select("github_links, datesandtimes")
            .eq("devpost_link", devpost_link_to_check)
            .maybe_single()
            .execute()
        )

        if not response.data:
            print(f"no data found for devpost_link: {devpost_link_to_check}")
            return {"error": f"no data found for devpost_link: {devpost_link_to_check}"}

        hackathon_data = response.data
        github_links_str_repr = hackathon_data.get("github_links")
        dates_and_times_str_repr = hackathon_data.get("datesandtimes")

        actual_github_links_list = []

        if isinstance(github_links_str_repr, str) and github_links_str_repr.strip():
            try:
                actual_github_links_list = json.loads(github_links_str_repr)
                if not isinstance(actual_github_links_list, list):
                    msg = f"parsed 'github_links' is not a list for {devpost_link_to_check}, parsed: {actual_github_links_list}"
                    print(msg)
                    return {"error": msg}
            except json.JSONDecodeError as jde:
                msg = f"error decoding JSON string from 'github_links' for {devpost_link_to_check}: {jde}, string was: {github_links_str_repr}"
                print(msg)
                return {"error": msg}
        elif github_links_str_repr is None or not github_links_str_repr.strip():
            print(
                f"no GitHub links string found or string is empty in db for {devpost_link_to_check}"
            )
        else:
            msg = f"'github_links' field is not a string or is in an unexpected format for {devpost_link_to_check}: {type(github_links_str_repr)}"
            print(msg)
            return {"error": msg}

        if not actual_github_links_list:
            print(
                f"no GitHub links to process for {devpost_link_to_check} after parsing"
            )
            supabase.table("devpost_hackathons").update(
                {"commit_validity_status": []}
            ).eq("devpost_link", devpost_link_to_check).execute()
            return {
                "message": "no GitHub links to process",
                "commit_validity_status": [],
            }

        # parsing dates and times of hackathon + doing some checks
        if not isinstance(dates_and_times_str_repr, str):
            msg = f"hackathon 'datesandtimes' field is not a string for {devpost_link_to_check}, expected string like '[\"date1\",\"date2\"]'."
            print(msg)
            return {"error": msg}
        try:
            dates_and_times_arr = json.loads(dates_and_times_str_repr)
        except json.JSONDecodeError as jde:
            msg = f"error decoding JSON string from 'datesandtimes' for {devpost_link_to_check}: {jde}, string was: {dates_and_times_str_repr}"
            print(msg)
            return {"error": msg}

        if not isinstance(dates_and_times_arr, list) or len(dates_and_times_arr) != 2:
            msg = f"parsed 'datesandtimes' is not a list of two elements for {devpost_link_to_check}, parsed: {dates_and_times_arr}"
            print(msg)
            return {"error": msg}

        # start + end dates of hackathon
        hackathon_start_str, hackathon_end_str = (
            dates_and_times_arr[0],
            dates_and_times_arr[1],
        )

        if not isinstance(hackathon_start_str, str) or not isinstance(
            hackathon_end_str, str
        ):
            msg = f"hackathon start or end date in parsed 'datesandtimes' array is not a string for {devpost_link_to_check}"
            print(msg)
            return {"error": msg}

        try:
            # parse ISO string
            hackathon_start_dt_local = datetime.fromisoformat(hackathon_start_str)
            hackathon_end_dt_local = datetime.fromisoformat(hackathon_end_str)

            # convert to UTC to be compared with git commits
            hackathon_start_dt_utc = hackathon_start_dt_local.astimezone(timezone.utc)
            hackathon_end_dt_utc = hackathon_end_dt_local.astimezone(timezone.utc)

            print(
                f"hackathon start: {hackathon_start_dt_utc} (UTC)"
            )
            print(
                f"hackathon end: {hackathon_end_dt_utc} (UTC)"
            )

        except ValueError as ve:
            return {"error": f"invalid hackathon date format or conversion issue: {ve}"}

        # now go through each github link
        commit_validity_status = []
        for gh_link in actual_github_links_list:
            if not isinstance(gh_link, str):
                # skip this github link
                commit_validity_status.append(False)
                continue

            if gh_link == "no GitHub link found":
                commit_validity_status.append("NA")
                continue

            sanitized_link = sanitize_github_url(gh_link)
            if not sanitized_link:
                # skip this github link
                commit_validity_status.append(False)
                continue

            # processing commits
            commit_info = get_first_last_commit(sanitized_link)

            if (
                "error" in commit_info
                or not commit_info.get("first_commit_date")
                or not commit_info.get("last_commit_date")
            ):
                print(
                    f"cannot get commit info for {sanitized_link}: {commit_info.get('error', 'Unknown error')}"
                )
                commit_validity_status.append(False)
                continue

            try:
                # git commits to UTC
                first_commit_dt_utc = datetime.fromisoformat(
                    commit_info["first_commit_date"].replace("Z", "+00:00")
                )
                last_commit_dt_utc = datetime.fromisoformat(
                    commit_info["last_commit_date"].replace("Z", "+00:00")
                )

                # the big check, is first + last commit within hackathon window?
                is_valid = (
                    first_commit_dt_utc >= hackathon_start_dt_utc
                    and last_commit_dt_utc <= hackathon_end_dt_utc
                    and first_commit_dt_utc <= last_commit_dt_utc
                )

                commit_validity_status.append(is_valid)
                if is_valid:
                    print(
                        f"VALID: {sanitized_link} (Commits: {first_commit_dt_utc} to {last_commit_dt_utc} UTC)"
                    )
                else:
                    print(
                        f"INVALID: {sanitized_link} (Commits: {first_commit_dt_utc} to {last_commit_dt_utc} UTC)"
                    )

            except ValueError as ve:
                print(f"error parsing commit dates for {sanitized_link}: {ve}")
                commit_validity_status.append(False)
            except Exception as e_commit_proc:
                print(
                    f"unexpected error processing commit dates for {sanitized_link}: {e_commit_proc}"
                )
                commit_validity_status.append(False)

        # send to supabase
        supabase.table("devpost_hackathons").update(
            {"commit_validity_status": commit_validity_status}
        ).eq("devpost_link", devpost_link_to_check).execute()

        print("commit_validity_status column updated to:"+ str(commit_validity_status))
        return {
            "devpost_link": devpost_link_to_check,
            "commit_validity_status": commit_validity_status,
        }

    except Exception as e:
        print(
            f"error in check_and_store_commit_validity for {devpost_link_to_check}: {e}"
        )
        return {"error": f"error occurred: {str(e)}"}


@app.route("/api/user-hackathons/<linkedin_id>")
def get_user_hackathons(linkedin_id):
    try:
        if not linkedin_id:
            return jsonify({'error': 'Invalid user ID'}), 400

        response = (
            supabase.table("devpost_hackathons")
            .select("linkedin_id, devpost_link, created_at")
            .eq("linkedin_id", linkedin_id)
            .execute()
        )

        if not response.data:
            return jsonify([])

        # cleaning up
        hackathons = []
        for item in response.data:
            try:
                url = item["devpost_link"]
                name = (
                    url.replace("https://", "")
                    .replace("http://", "")
                    .split(".devpost.com")[0]
                )

                hackathons.append(
                    {
                        "linkedin_id": item["linkedin_id"],
                        "devpost_link": url,
                        "name": name,
                        "created_at": item["created_at"],
                    }
                )
            except KeyError as e:
                print(f"missing key in hackathon data: {e}")
                continue

        return jsonify(hackathons)

    except Exception as e:
        print(f"Error fetching hackathons: {str(e)}")
        return jsonify({"error": str(e)}), 500


def lambda_handler(event, context):
    from werkzeug.wrappers import Request, Response
    from werkzeug.wsgi import responder
    from werkzeug.exceptions import HTTPException

    @responder
    def application(environ, start_response):
        try:
            return app(environ, start_response)
        except HTTPException as e:
            return e

    return Request(event).get_response(application)


# run flask app
if __name__ == "__main__":
    app.run(port=8000)
    # app.run()

else:

    def create_app():
        return app

    api = create_app()
