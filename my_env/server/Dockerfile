FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY . .
RUN pip install --no-cache-dir -r server/requirements.txt


# HF Spaces uses port 7860
EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
