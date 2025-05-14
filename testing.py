import sys
import os
from supabase import create_client
from datetime import datetime, timezone

# function to test
from app import (
    get_git_commit_history,
    sanitize_github_url, 
    scrape_devpost_link,
    get_all_github_links,
    SUPABASE_KEY,
    SUPABASE_URL,
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def test_find_projects():
    TEST_URL = "https://cuhacking6.devpost.com"
    print(f"testing with {TEST_URL}")

    scrape_devpost_link(TEST_URL)

    # verify
    result = (
        supabase.table("devpost_hackathons")
        .select("*")
        .eq("devpost_link", TEST_URL)
        .execute()
    )

    if result.data and len(result.data) > 0:
        project_links = result.data[0]["project_links"]
        links_list = [
            link.strip(' "') for link in project_links.split(",") if link.strip()
        ]

        if project_links:
            print(f"test: found {len(links_list)} total projects")

        else:
            print("test: found record but no projects")
    else:
        print("test: no data found")

def test_find_githubs():
    TEST_URL = "https://cuhacking6.devpost.com"
    print(f"testing with {TEST_URL}")

    get_all_github_links(TEST_URL)

    # verify
    result = (
        supabase.table("devpost_hackathons")
        .select("*")
        .eq("devpost_link", TEST_URL)
        .execute()
    )
    if result.data and len(result.data) > 0:
        github_links = result.data[0]["github_links"]
        links_list = [
            link.strip(' "') for link in github_links.split(",") if link.strip()
        ]

        if github_links:
            print(f"test: found {len(links_list)} total githubs")

        else:
            print("test: found record but no githubs")
    else:
        print("test: no data found")

def test_sanitize_github_link():
    TEST_URL = "https://github.com/isharghura/HackVerify/pulls"
    print(f"testing with {TEST_URL}")

    sanitize_github_url(TEST_URL)

def get_first_and_last_commit_times():
    TEST_URL = "https://github.com/isharghura/HackVerify"
    print(f"testing with {TEST_URL}")
    get_git_commit_history(TEST_URL)

if __name__ == "__main__":
    get_first_and_last_commit_times()
