FROM python:3.11-slim

WORKDIR /app

# Zainstaluj zależności systemowe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopiuj requirements i zainstaluj
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiuj kod
COPY . .

# Port dla HF Spaces
EXPOSE 7860

# Uruchom
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]