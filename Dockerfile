FROM python:3.11-slim

# Instalar LibreOffice e Node.js 18
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dependências Node
COPY package.json .
RUN npm install

# Copiar código
COPY app/ ./app/

# Porta
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
