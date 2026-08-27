import os
from dotenv import load_dotenv
load_dotenv()
def get_config(key="ccplatform"):
    return {
        "userName": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "schema": os.getenv("DB_NAME")
    }