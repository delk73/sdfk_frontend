# Use the official Python image from the Docker Hub  
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .
  
# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy the .env file into the container
COPY .env .env

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]