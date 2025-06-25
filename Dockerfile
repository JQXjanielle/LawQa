# Use Python base image
FROM python:3.10

# Set working directory in container
WORKDIR /app

# Copy all files into container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the correct port (Hugging Face expects 7860)
EXPOSE 7860

# Start the Flask app
CMD ["python", "app.py"]

