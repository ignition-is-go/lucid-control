FROM python:2.7.14

WORKDIR /app/

# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt
COPY Pipfile.lock ./
COPY Pipfile ./
RUN pip install pipenv
RUN pipenv install --deploy --system

# create unprivileged user
RUN adduser --disabled-password --gecos '' myuser  