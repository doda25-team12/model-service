# Use an official lightweight Python image
FROM python:3.12.9-slim

# Set working directory inside container
WORKDIR /app

# Install system-level dependencies for numpy, scipy, matplotlib, sklearn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Expose Flask default port
EXPOSE 8081

# Run the Flask app
# Replace app.py with your actual entry file
CMD ["python", "src/serve_model.py"]
