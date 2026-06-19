# Exprompt — Prompt Factory

> Transforme un brief en prompt prêt à copier-coller.
> Pipeline : **INTAKE → CREATIVE_WRITER → AUTO_QA**

Exprompt est un outil CLI + API qui automatise la création de prompts pour la génération de contenu (vidéo, image). Inspiré des 97 system prompts des meilleurs outils IA (Cursor, Claude Code, Windsurf, v0, Perplexity...).

## Installation

```bash
# Avec uv (recommandé)
uv pip install -e .

# Avec pip
pip install -e .
```

## Utilisation

### CLI

```bash
# Brief direct
exprompt "Pub TikTok pour BugCrush, 15s, avant-après..."

# Depuis un fichier
exprompt --file brief.txt

# Depuis stdin
echo "Pub Instagram..." | exprompt

# Mode strict (pose des questions si infos manquantes)
exprompt -m strict "Crée un prompt pour..."

# Sortie JSON
exprompt --json "Brief..."
```

### API

```bash
# Lancer le serveur
exprompt serve

# Ou via Docker
docker compose up -d
```

```bash
curl -X POST http://localhost:8022/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "Pub TikTok pour BugCrush, 15s, avant-après...",
    "mode": "autonome"
  }'
```

### Docker

```bash
# Copier la config
cp .env.example .env
# Éditer .env avec ta clé API

# Lancer
docker compose up -d

# Vérifier
curl http://localhost:8022/health
```

## Pipeline

```
Brief Utilisateur
    ↓
[1] INTAKE — analyse du brief → spec structurée YAML
    ↓
[2] CREATIVE_WRITER — spec → deliverable_prompt
    ↓
[3] AUTO_QA — validation qualité (10 critères)
    ↓
Livraison : spec + prompt + QA + variants
```

### Modes

- **`autonome`** (défaut) : si infos manquantes → assumptions explicites, on continue
- **`strict`** : si infos manquantes → 3-5 questions, on attend les réponses

## Configuration

Variables d'environnement (`.env`) :

| Variable | Défaut | Description |
|---|---|---|
| `LLM_PROVIDER` | `deepseek` | openai / deepseek / openrouter / custom |
| `LLM_MODEL` | `deepseek-chat` | Modèle à utiliser |
| `LLM_API_KEY` | — | Clé API |
| `LLM_BASE_URL` | `https://api.deepseek.com` | URL de l'API |
| `HOST` | `0.0.0.0` | Hôte du serveur |
| `PORT` | `8022` | Port du serveur |

## Stack

- **Python 3.11+** — cœur du pipeline
- **FastAPI** — API REST
- **Typer** — CLI
- **OpenAI SDK** — communication LLM (compatible DeepSeek, OpenRouter, etc.)
- **Pydantic** — modèles et validation
- **Docker** — déploiement production

## Crédits

- **Ibrahima Xaliloulah Ndiaye** (xalil05) — Conception, briefs, direction et validation du projet
- [Hermes Agent](https://hermes-agent.nousresearch.com) — Assistant IA d'exécution
- Prompt Engineering Guide, PROMPT_ENGENERING, system-prompts-and-models — Sources d'inspiration
