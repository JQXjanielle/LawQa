# Use a Python base image
FROM python:3.12

# Set working directory inside the container
WORKDIR /app

# Copy all project files into the container
COPY . /app

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Hugging Face Spaces expects
EXPOSE 7860

# Run your Flask app
CMD ["python", "app.py"]
