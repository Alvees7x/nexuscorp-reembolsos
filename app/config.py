"""Configurações lidas de variáveis de ambiente (nada sensível fica no código)."""
import os
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reembolsos.db")

# Sem SECRET_KEY definida, gera uma chave aleatória por processo (tokens deixam de valer
# a cada reinício). Em produção, defina SECRET_KEY.
SECRET_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30") or secrets.token_urlsafe(48)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
