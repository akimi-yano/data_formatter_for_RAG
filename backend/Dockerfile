# Use official Python runtime
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirement file
COPY requirements.txt .

# Install dependencies (including system libs for ReportLab if needed)
# ReportLab might need minimal build tools, but 'slim' often works for basic usage.
# If issues arise, we might need 'build-essential'.
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port (default for some cloud providers)
EXPOSE 8000

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
