from http.server import BaseHTTPRequestHandler
from bs4 import BeautifulSoup
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        test_url = "https://cuhacking6.devpost.com"
        all_project_links = []
        pg_num = 1

        # scrape through devpost to find all projects
        while True:
            print(f"getting all projects on page {pg_num}")

            proj_gallery_url = f"{test_url}/project-gallery?page={pg_num}"
            result = requests.get(proj_gallery_url)
            gallery = BeautifulSoup(result.text, "html.parser")

            # project link location
            curr_project_links = gallery.find_all(
                "a", class_="block-wrapper-link fade link-to-software"
            )

            if not curr_project_links:
                print(f"no projects on page {pg_num}")
                break

            for link in curr_project_links:
                all_project_links.append(link["href"])

            pg_num += 1

        all_github_links = []

        # scrape through each project
        for project_link in all_project_links:
            result = requests.get(project_link)
            project = BeautifulSoup(result.text, "html.parser")

            # find github repo link
            for a_tag in project.find_all("a", href=True):
                if "github.com" in a_tag["href"]:
                    github_link = a_tag["href"]
                    break

            if github_link:
                print(f"found {github_link} from {project_link}")
                all_github_links.append(github_link)
            else:
                print("couldn't find github link")
                all_github_links.append(f"no github link found for: {project_link}")

        self.wfile.write(str(all_github_links).encode())
        return