from dotenv import load_dotenv

from app import create_app

load_dotenv(".env.local")

# run flask app
app = create_app()
if __name__ == "__main__":
    app.run(port=8000)