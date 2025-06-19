FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Install only allowed Python packages
RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    pandas==2.0.3 \
    matplotlib==3.7.2 \
    scikit-learn==1.3.0 \
    requests==2.31.0

# Create output directory
RUN mkdir -p /workspace/output

# Copy bioreactor client library
COPY bioreactor_client.py /workspace/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash experiment_user
RUN chown -R experiment_user:experiment_user /workspace
USER experiment_user

# Set read-only filesystem except for output directory
VOLUME ["/workspace/output"]

# Default command
CMD ["python", "/workspace/user_script.py"] 
