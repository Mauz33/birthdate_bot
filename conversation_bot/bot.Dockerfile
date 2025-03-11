FROM python:3.10-slim
WORKDIR /app

COPY ./conversation_bot /app/conversation_bot
COPY ./db /app/db
COPY ./notification_service /app/notification_service
COPY .env .env
COPY requirements.txt requirements.txt
COPY utils.py utils.py

RUN ls
RUN ls /app

RUN apt-get update -y
RUN pip install -r requirements.txt

ENV PYTHONPATH=/app
CMD ["python", "conversation_bot/main.py"]


