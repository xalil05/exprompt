FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

# Port de l'API
EXPOSE 8022

# Par défaut : lancer le serveur API
CMD ["exprompt", "serve"]
