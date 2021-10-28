FROM python:3.8

WORKDIR /bot

COPY requirements.txt requirements.txt

ENV SPREADSHEET_ID=
ENV API_TOKEN=
ENV PAYMENT_TOKEN=
ENV EMAIL_FROM=
ENV EMAIL_PASSWORD=
ENV COST=

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt && apt-get update && apt-get install sqlite3
RUN sqlite3 dbdata/tickets.db
RUN pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

COPY . .

CMD ["python", "main.py"]