FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python packages
RUN pip install --no-cache-dir \
    requests \
    numpy \
    pandas \
    matplotlib \
    scikit-learn

# Copy bioreactor client library
COPY bioreactor_client.py /app/

# Create output directory
RUN mkdir -p /app/output

# Set environment variables
ENV PYTHONPATH=/app
ENV BIOREACTOR_NODE_API_URL=http://host.docker.internal:9000

# Default command
CMD ["python", "/app/user_script.py"] 
