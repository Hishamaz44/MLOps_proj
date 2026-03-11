# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install dependencies first (for better Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY main.py .

# Expose the API port
EXPOSE 8000

# Start the application (Updated to main:app!)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]