# Porsafzar

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-FF1709?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

###  A powerful, enterprise-ready survey platform built on **Django + DRF** and compatible with SurveyJS with supporting advanced analytics, versioning, target audiences, live results, and more.


# Key Features

## 1. Upload & Manage Survey JSONs
- Upload SurveyJS schemas directly  
- Store every version  
- Soft-delete versions  
- Mark active version for responses  

## 2. Survey Configuration
Each survey supports:
- Enable/disable  
- Active time window  
- Limit responses per user  
- Allow/disallow editing responses  

## 3. Edit Submitted Responses
If enabled:
- Logged-in users can edit previous answers  
- Pre-filled responses shown  

## 4. Target Audience System
Define who can answer a survey:
- Roles: Student, Staff, Professor, Services, Management  
- Inclusion/exclusion rules  
- Add/remove phone numbers  
- Save audience groups for reuse  

## 5. Version-Based Analytics
- Filter results by survey version  
- Keep deleted versions hidden (soft delete)  

## 6. Results: Tables & Charts
- Structured statistical data (API-compatible)  
- Export results to Excel  
- Download chart images  

## 7. One-Time Answer Links
- Generate one-time-use URLs  
- Export links (Excel)  
- Optional: send via SMS/email  

## 8. Pre-Built Template Surveys
- Admin-defined templates  
- Creators can re-use verified forms  

## 9. Live Responses (WebSocket)
- Real-time statistics  
- Public display, no login  
- Perfect for events & elections  

## 10. Combined Charts
- Combine two questions for cross-analysis  
- Example: Education Level × Gender  

---

# Project Phases

## **Phase 1**
- Upload/store SurveyJS JSON  
- Version management  
- Survey configuration  
- Editable response logic  

## **Phase 2**
- Target audience  
- Version-based analytics  
- Saved audience groups  
- Results tables & charts  
- One-time links  

## **Phase 3**
- Template surveys  
- WebSocket live results  
- Combined charts  

---

# Requirements
- Python 3.x  
- Django  
- Django REST Framework  
- Django Channels
- Django Filter  
- Redis  
- Celery  
- Docker  

---

# Environment Variables (`.env`)
```
# Database
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
DATABASE_URL=

# PGAdmin
PGADMIN_DEFAULT_EMAIL=
PGADMIN_DEFAULT_PASSWORD=


# Celery
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
CELERY_FLOWER_USER=
CELERY_FLOWER_PASSWORD=

# Redis Cache
REDIS_CACHE_LOCATION=

#OTP
PHONE_SECRET_KEY=

```

---

# How to Run
1. Build and start containers:
   ```
   docker-compose up -d --build
   ```
2. Access services:
   - Django app: http://localhost:8000
   - Flower (Celery monitoring): http://localhost:5555
   - Pgadmin: http://localhost:5050
3. To stop:
   ```
   docker-compose down
   ```
4. To test:
   ```
   make pytest
   or 
   make pytest-cov
   ```

