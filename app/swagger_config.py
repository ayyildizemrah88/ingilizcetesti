# -*- coding: utf-8 -*-
"""
Swagger/OpenAPI Configuration
"""

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/"
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Skills Test Center API",
        "description": """
## International English Proficiency Testing API

This API provides programmatic access to the Skills Test Center platform for:
- Managing exam candidates
- Accessing question banks
- Retrieving exam results
- Configuring webhooks

### Authentication

All API endpoints require an API key. Include it in the request header:

```
X-API-KEY: your-api-key-here
```

### Rate Limits

- Standard: 100 requests per minute
- Bulk operations: 10 requests per minute

### Webhooks

Configure webhooks to receive real-time notifications for:
- `exam.completed` - When a candidate finishes their exam
- `candidate.created` - When a new candidate is added

Webhook payloads are signed with HMAC-SHA256 using your API key.
        """,
        "version": "2.0.0",
        "termsOfService": "/terms",
        "contact": {
            "name": "API Support",
            "email": "api@skillstestcenter.com"
        }
    },
    "host": "",  # Will be set dynamically
    "basePath": "/api",
    "schemes": ["https", "http"],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "name": "X-API-KEY",
            "in": "header",
            "description": "API key for authentication"
        }
    },
    "security": [
        {"ApiKeyAuth": []}
    ],
    "tags": [
        {
            "name": "Candidates",
            "description": "Manage exam candidates"
        },
        {
            "name": "Questions",
            "description": "Question bank management"
        },
        {
            "name": "Exam",
            "description": "Exam flow and results"
        },
        {
            "name": "Webhooks",
            "description": "Webhook configuration and testing"
        },
        {
            "name": "Authentication",
            "description": "Login and session management"
        },
        {
            "name": "Admin",
            "description": "Admin panel operations"
        }
    ],
    "definitions": {
        "Candidate": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "ad_soyad": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "giris_kodu": {"type": "string"},
                "puan": {"type": "number"},
                "seviye_sonuc": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2"]},
                "sinav_durumu": {"type": "string", "enum": ["beklemede", "devam_ediyor", "tamamlandi"]}
            }
        },
        "CandidateInput": {
            "type": "object",
            "required": ["ad_soyad"],
            "properties": {
                "ad_soyad": {"type": "string", "description": "Full name"},
                "email": {"type": "string", "format": "email"},
                "tc_kimlik": {"type": "string", "maxLength": 11},
                "sinav_suresi": {"type": "integer", "minimum": 5, "maximum": 180},
                "soru_limiti": {"type": "integer", "minimum": 5, "maximum": 100},
                "send_email": {"type": "boolean", "default": False}
            }
        },
        "Question": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "soru_metni": {"type": "string"},
                "secenek_a": {"type": "string"},
                "secenek_b": {"type": "string"},
                "secenek_c": {"type": "string"},
                "secenek_d": {"type": "string"},
                "kategori": {"type": "string"},
                "zorluk": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2"]}
            }
        },
        "ExamResult": {
            "type": "object",
            "properties": {
                "puan": {"type": "number"},
                "cefr_level": {"type": "string"},
                "band_score": {"type": "number"},
                "skills": {
                    "type": "object",
                    "properties": {
                        "grammar": {"type": "number"},
                        "vocabulary": {"type": "number"},
                        "reading": {"type": "number"},
                        "listening": {"type": "number"},
                        "writing": {"type": "number"},
                        "speaking": {"type": "number"}
                    }
                }
            }
        },
        "Error": {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "message": {"type": "string"}
            }
        }
    }
}
