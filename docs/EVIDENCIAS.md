# Evidências de execução

Gerado automaticamente por `python -m scripts.gerar_evidencias` (tokens abreviados).


## Cenário 01 — Acesso indevido

```http
POST /expenses   [bruno]
{
  "category": "transporte",
  "amount": "999.99",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-1"
}
```
**→ HTTP 201**
```json
{
  "id": 1,
  "requester": {
    "id": 2,
    "name": "Bruno",
    "department": {
      "id": 2,
      "name": "Tecnologia"
    }
  },
  "category": "transporte",
  "amount": "999.99",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-1",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:41.830856",
  "updated_at": "2026-11-04T13:29:41.830863"
}
```

```http
GET /expenses/1   [ana]
```
**→ HTTP 404**
```json
{
  "error": {
    "code": "nao_encontrado",
    "message": "Solicitação não encontrada"
  }
}
```


## Cenário 02 — Gestor de outro departamento

```http
POST /expenses   [bruno]
{
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-2"
}
```
**→ HTTP 201**
```json
{
  "id": 2,
  "requester": {
    "id": 2,
    "name": "Bruno",
    "department": {
      "id": 2,
      "name": "Tecnologia"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-2",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:41.866828",
  "updated_at": "2026-11-04T13:29:41.866834"
}
```

```http
POST /expenses/2/submit   [bruno]
```
**→ HTTP 200**
```json
{
  "id": 2,
  "requester": {
    "id": 2,
    "name": "Bruno",
    "department": {
      "id": 2,
      "name": "Tecnologia"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-2",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:41.866828",
  "updated_at": "2026-11-04T13:29:41.880598"
}
```

```http
POST /manager/expenses/2/approve   [patricia]
```
**→ HTTP 404**
```json
{
  "error": {
    "code": "nao_encontrado",
    "message": "Solicitação não encontrada"
  }
}
```

```http
GET /expenses/2   [bruno]
```
**→ HTTP 200**
```json
{
  "id": 2,
  "requester": {
    "id": 2,
    "name": "Bruno",
    "department": {
      "id": 2,
      "name": "Tecnologia"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-2",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:41.866828",
  "updated_at": "2026-11-04T13:29:41.880598"
}
```


## Cenário 03 — Credenciais incorretas

```http
POST /auth/login
{
  "email": "ana@nexuscorp.com",
  "password": "***"
}
```
**→ HTTP 401**
```json
{
  "error": {
    "code": "credenciais_invalidas",
    "message": "E-mail ou senha inválidos"
  }
}
```

```http
POST /auth/login
{
  "email": "inexistente@nexuscorp.com",
  "password": "***"
}
```
**→ HTTP 401**
```json
{
  "error": {
    "code": "credenciais_invalidas",
    "message": "E-mail ou senha inválidos"
  }
}
```


## Cenário 04 — Tentativa de alteração de permissões

```http
POST /auth/register
{
  "name": "Mallory",
  "email": "m@x.com",
  "password": "***",
  "department_id": 3,
  "role": "financeiro"
}
```
**→ HTTP 422**
```json
{
  "error": {
    "code": "dados_invalidos",
    "message": "Os dados enviados são inválidos",
    "details": [
      {
        "field": "role",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

```http
PATCH /users/me   [ana]
{
  "role": "financeiro"
}
```
**→ HTTP 422**
```json
{
  "error": {
    "code": "dados_invalidos",
    "message": "Os dados enviados são inválidos",
    "details": [
      {
        "field": "name",
        "message": "Field required"
      },
      {
        "field": "role",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

```http
PATCH /users/me   [ana]
{
  "department_id": 3
}
```
**→ HTTP 422**
```json
{
  "error": {
    "code": "dados_invalidos",
    "message": "Os dados enviados são inválidos",
    "details": [
      {
        "field": "name",
        "message": "Field required"
      },
      {
        "field": "department_id",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

```http
GET /finance/expenses   [ana]
```
**→ HTTP 403**
```json
{
  "error": {
    "code": "acesso_negado",
    "message": "Seu perfil não tem permissão para esta operação"
  }
}
```


## Cenário 05 — Aprovação fora da sequência

```http
POST /expenses   [ana]
{
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-5"
}
```
**→ HTTP 201**
```json
{
  "id": 3,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-5",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:42.239045",
  "updated_at": "2026-11-04T13:29:42.239051"
}
```

```http
POST /expenses/3/submit   [ana]
```
**→ HTTP 200**
```json
{
  "id": 3,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-5",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:42.239045",
  "updated_at": "2026-11-04T13:29:42.252726"
}
```

```http
POST /finance/expenses/3/approve   [marina]
```
**→ HTTP 409**
```json
{
  "error": {
    "code": "transicao_invalida",
    "message": "Operação incompatível com a situação atual da solicitação"
  }
}
```


## Cenário 06 — Manipulação após o envio (R$ 180,00 → R$ 1.800,00)

```http
PATCH /expenses/3   [ana]
{
  "amount": "1800.00"
}
```
**→ HTTP 409**
```json
{
  "error": {
    "code": "solicitacao_nao_editavel",
    "message": "A solicitação não pode mais ser alterada"
  }
}
```

```http
GET /expenses/3   [ana]
```
**→ HTTP 200**
```json
{
  "id": 3,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-5",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:42.239045",
  "updated_at": "2026-11-04T13:29:42.252726"
}
```


## Cenário 07 — Consulta com filtros

```http
POST /expenses   [bruno]
{
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-7"
}
```
**→ HTTP 201**
```json
{
  "id": 4,
  "requester": {
    "id": 2,
    "name": "Bruno",
    "department": {
      "id": 2,
      "name": "Tecnologia"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-7",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:42.302510",
  "updated_at": "2026-11-04T13:29:42.302516"
}
```

```http
POST /expenses/4/submit   [bruno]
```
**→ HTTP 200**
```json
{
  "id": 4,
  "requester": {
    "id": 2,
    "name": "Bruno",
    "department": {
      "id": 2,
      "name": "Tecnologia"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-BRUNO-7",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:42.302510",
  "updated_at": "2026-11-04T13:29:42.315677"
}
```

```http
GET /manager/expenses?status=aguardando_gestor   [patricia]
```
**→ HTTP 200**
```json
[
  {
    "id": 3,
    "requester": {
      "id": 1,
      "name": "Ana",
      "department": {
        "id": 1,
        "name": "Comercial"
      }
    },
    "category": "transporte",
    "amount": "180.00",
    "expense_date": "2026-11-04",
    "justification": "Deslocamento para cliente",
    "receipt_ref": "NF-ANA-5",
    "status": "aguardando_gestor",
    "created_at": "2026-11-04T13:29:42.239045",
    "updated_at": "2026-11-04T13:29:42.252726"
  }
]
```

```http
GET /manager/expenses?department_id=2   [patricia]
```
**→ HTTP 403**
```json
{
  "error": {
    "code": "acesso_negado",
    "message": "Gestor só pode consultar o próprio departamento"
  }
}
```


## Cenário 08 — Fluxo completo e histórico

```http
POST /expenses   [ana]
{
  "category": "hospedagem",
  "amount": "320.50",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-8"
}
```
**→ HTTP 201**
```json
{
  "id": 5,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "hospedagem",
  "amount": "320.50",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-8",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:42.369543",
  "updated_at": "2026-11-04T13:29:42.369549"
}
```

```http
POST /expenses/5/submit   [ana]
```
**→ HTTP 200**
```json
{
  "id": 5,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "hospedagem",
  "amount": "320.50",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-8",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:42.369543",
  "updated_at": "2026-11-04T13:29:42.382738"
}
```

```http
POST /manager/expenses/5/approve   [patricia]
{
  "comment": "Despesa de cliente confirmada"
}
```
**→ HTTP 200**
```json
{
  "id": 5,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "hospedagem",
  "amount": "320.50",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-8",
  "status": "aguardando_financeiro",
  "created_at": "2026-11-04T13:29:42.369543",
  "updated_at": "2026-11-04T13:29:42.397617"
}
```

```http
POST /finance/expenses/5/approve   [marina]
{
  "comment": "Conferido"
}
```
**→ HTTP 200**
```json
{
  "id": 5,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "hospedagem",
  "amount": "320.50",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-8",
  "status": "aprovada",
  "created_at": "2026-11-04T13:29:42.369543",
  "updated_at": "2026-11-04T13:29:42.412282"
}
```

```http
POST /finance/expenses/5/pay   [marina]
```
**→ HTTP 200**
```json
{
  "id": 5,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "hospedagem",
  "amount": "320.50",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-8",
  "status": "paga",
  "created_at": "2026-11-04T13:29:42.369543",
  "updated_at": "2026-11-04T13:29:42.426916"
}
```

```http
GET /expenses/5/history   [ana]
```
**→ HTTP 200**
```json
[
  {
    "id": 4,
    "stage": "colaborador",
    "decision": "enviada",
    "reviewer": {
      "id": 1,
      "name": "Ana",
      "role": "colaborador"
    },
    "comment": null,
    "created_at": "2026-11-04T13:29:42.382738"
  },
  {
    "id": 5,
    "stage": "gestor",
    "decision": "aprovada",
    "reviewer": {
      "id": 3,
      "name": "Patrícia",
      "role": "gestor"
    },
    "comment": "Despesa de cliente confirmada",
    "created_at": "2026-11-04T13:29:42.397617"
  },
  {
    "id": 6,
    "stage": "financeiro",
    "decision": "aprovada",
    "reviewer": {
      "id": 6,
      "name": "Marina",
      "role": "financeiro"
    },
    "comment": "Conferido",
    "created_at": "2026-11-04T13:29:42.412282"
  },
  {
    "id": 7,
    "stage": "financeiro",
    "decision": "paga",
    "reviewer": {
      "id": 6,
      "name": "Marina",
      "role": "financeiro"
    },
    "comment": null,
    "created_at": "2026-11-04T13:29:42.426916"
  }
]
```

```http
PATCH /expenses/5   [ana]
{
  "amount": "1.00"
}
```
**→ HTTP 409**
```json
{
  "error": {
    "code": "solicitacao_nao_editavel",
    "message": "A solicitação não pode mais ser alterada"
  }
}
```


## Extra — Recusa sem justificativa (RN11) e autoaprovação (RN09)

```http
POST /expenses   [ana]
{
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-9"
}
```
**→ HTTP 201**
```json
{
  "id": 6,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-9",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:42.471002",
  "updated_at": "2026-11-04T13:29:42.471009"
}
```

```http
POST /expenses/6/submit   [ana]
```
**→ HTTP 200**
```json
{
  "id": 6,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-9",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:42.471002",
  "updated_at": "2026-11-04T13:29:42.484991"
}
```

```http
POST /manager/expenses/6/reject   [patricia]
{}
```
**→ HTTP 422**
```json
{
  "error": {
    "code": "dados_invalidos",
    "message": "Os dados enviados são inválidos",
    "details": [
      {
        "field": "comment",
        "message": "Field required"
      }
    ]
  }
}
```

```http
POST /manager/expenses/6/reject   [patricia]
{
  "comment": "Comprovante ilegível"
}
```
**→ HTTP 200**
```json
{
  "id": 6,
  "requester": {
    "id": 1,
    "name": "Ana",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-ANA-9",
  "status": "recusada",
  "created_at": "2026-11-04T13:29:42.471002",
  "updated_at": "2026-11-04T13:29:42.511563"
}
```

```http
POST /expenses   [patricia]
{
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-PAT-1"
}
```
**→ HTTP 201**
```json
{
  "id": 7,
  "requester": {
    "id": 3,
    "name": "Patrícia",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-PAT-1",
  "status": "rascunho",
  "created_at": "2026-11-04T13:29:42.526993",
  "updated_at": "2026-11-04T13:29:42.526999"
}
```

```http
POST /expenses/7/submit   [patricia]
```
**→ HTTP 200**
```json
{
  "id": 7,
  "requester": {
    "id": 3,
    "name": "Patrícia",
    "department": {
      "id": 1,
      "name": "Comercial"
    }
  },
  "category": "transporte",
  "amount": "180.00",
  "expense_date": "2026-11-04",
  "justification": "Deslocamento para cliente",
  "receipt_ref": "NF-PAT-1",
  "status": "aguardando_gestor",
  "created_at": "2026-11-04T13:29:42.526993",
  "updated_at": "2026-11-04T13:29:42.540842"
}
```

```http
POST /manager/expenses/7/approve   [patricia]
```
**→ HTTP 403**
```json
{
  "error": {
    "code": "segregacao_de_funcoes",
    "message": "Ninguém pode analisar uma solicitação de sua própria autoria"
  }
}
```
