"""Configurações lidas de variáveis de ambiente (nada sensível fica no código)."""
import os
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reembolsos.db")

# Sem SECRET_KEY definida, gera uma chave aleatória por processo (tokens deixam de valer
# a cada reinício). Em produção, defina SECRET_KEY.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48) # FALHA AO SUBIR SE NÃO ESTIVER GERADA
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
