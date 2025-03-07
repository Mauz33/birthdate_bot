FROM python:3.10-slim
WORKDIR /app

COPY . .

RUN apt-get update -y && apt-get install -y cron bash
RUN pip install -r requirements.txt

#ENTRYPOINT ["/bin/bash", "-c"]
CMD ["python", "main.py"]


