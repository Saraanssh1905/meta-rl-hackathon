FROM python:3.11-slim

WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r server/requirements.txt

# Expose port (HF Spaces expects 7860)
EXPOSE 7860

# Run the app
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
