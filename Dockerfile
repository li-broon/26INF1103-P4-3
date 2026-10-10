FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a Directory for Data Files
COPY . .
RUN mkdir -p data

# Load the API key from the copied .env file (unless one was already passed in with --env-file or -e)
CMD ["sh", "-c", "if [ -z \"$GEMINI_API_KEY\" ] && [ -f .env ]; then export $(grep -v '^#' .env | tr -d '\\r' | xargs); fi; exec python main.py"]