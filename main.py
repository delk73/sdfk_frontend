# main.py  
  
import streamlit as st  
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
database_url = os.getenv('DATABASE_URL')
postgres_port = os.getenv('POSTGRES_PORT')

if not database_url:
    raise ValueError("DATABASE_URL is not set or is empty.")
if not postgres_port:
    raise ValueError("POSTGRES_PORT is not set or is empty.")
#DEBUG
# print(f"Database URL: {database_url}")
# print(f"Postgres Port: {postgres_port}")

# Title of the app  
st.title("Color Curves CRUD and Search App")  
  
# Sidebar for navigation  
st.sidebar.title("Navigation")  
pages = {  
    "Read": "read.py",
    "Work": "work.py",  
}  
  
# Create a selectbox for page selection  
page = st.sidebar.selectbox("Select a page", list(pages.keys()))  
  
# Load the selected page  
with open(pages[page]) as f:  
    exec(f.read())