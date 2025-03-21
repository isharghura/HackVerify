from bs4 import BeautifulSoup
import requests

test_url = "https://cuhacking6.devpost.com"

all_project_links = []
pg_num = 1

while True:

    proj_gallery_url = f"{test_url}/project-gallery?page={pg_num}"

    result = requests.get(proj_gallery_url)
    gallery = BeautifulSoup(result.text, "html.parser")

    curr_project_links = gallery.find_all("a", class_="block-wrapper-link fade link-to-software")

    if not curr_project_links:
        break

    for link in curr_project_links:
        all_project_links.append(link["href"])

    pg_num+=1

for link in all_project_links:
    print(link)