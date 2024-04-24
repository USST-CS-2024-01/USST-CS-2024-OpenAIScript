FROM python:3.11-alpine
LABEL maintainer="vvbbnn00"
LABEL email="vvbbnn00@foxmail.com"

WORKDIR /app
RUN apk add --no-cache git openssh-client
COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app
CMD ["python", "main.py"]