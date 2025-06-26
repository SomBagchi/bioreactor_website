FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ .

# Create SSH keys directory
RUN mkdir -p /app/ssh_keys

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"] 
