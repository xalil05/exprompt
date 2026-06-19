"""Chargement des prompts système depuis les fichiers YAML/Markdown."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str, **kwargs) -> str:
    """Charge un prompt système et applique les variables simples.

    Args:
        name: Nom du fichier (sans extension). ex: 'intake', 'creative_writer'
        **kwargs: Variables à substituer dans le prompt avec {{ variable }}
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        msg = f"Prompt '{name}' introuvable dans {PROMPTS_DIR}"
        raise FileNotFoundError(msg)

    content = path.read_text(encoding="utf-8")

    # Gestion simple du {% if mode == "xxx" %}
    mode_val = kwargs.get("mode", "")
    lines = content.split("\n")
    output = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("{% if mode =="):
            # Si la condition correspond, on ne skip pas
            expected = stripped.split('"')[1] if '"' in stripped else ""
            skip = mode_val != expected
            continue
        if stripped == "{% else %}":
            skip = not skip
            continue
        if stripped.startswith("{% endif %}"):
            skip = False
            continue
        if not skip:
            output.append(line)
    content = "\n".join(output)

    # Substitution simple {{ variable }} → valeur
    for key, val in kwargs.items():
        content = content.replace(f"{{{{ {key} }}}}", str(val))

    return content
