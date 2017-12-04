FROM python:2

WORKDIR /app/

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# create unprivileged user
RUN adduser --disabled-password --gecos '' myuser  