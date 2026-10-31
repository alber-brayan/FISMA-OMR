"""Valores de esta edición; claves internas V2 salon/curso se conservan."""
import re
import unicodedata

LEVELS = ("Nivel VI", "Nivel VII")
SECTORS = ("Publico", "Privado")

def key(value):
    plain = unicodedata.normalize("NFKD", str(value or ""))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in plain if not unicodedata.combining(c)).lower())

def level(value):
    return {"vi": LEVELS[0], "6": LEVELS[0], "nivelvi": LEVELS[0], "nivel6": LEVELS[0],
            "vii": LEVELS[1], "7": LEVELS[1], "nivelvii": LEVELS[1], "nivel7": LEVELS[1]}.get(key(value))

def sector(value):
    return {"publico": SECTORS[0], "publica": SECTORS[0],
            "privado": SECTORS[1], "privada": SECTORS[1]}.get(key(value))

def sector_label(value):
    return "Público" if sector(value) == "Publico" else "Privado"
