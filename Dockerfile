FROM python:3.11-slim

WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r server/requirements.txt

# Expose port (HF Spaces routes to first EXPOSE command)
EXPOSE 8000

# Run the app
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
