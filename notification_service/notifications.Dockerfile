FROM python:3.10-slim
WORKDIR /app

COPY notification_service.py db_interact.py requirements.txt .env utils.py .

RUN apt-get update -y && apt-get install -y cron bash
RUN pip install -r requirements.txt

#ENTRYPOINT ["/bin/bash", "-c"]
CMD ["python", "notification_service.py"]


