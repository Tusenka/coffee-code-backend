FROM python:3.13-slim

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

COPY . /usr/src/app

ENTRYPOINT ["python", "app.py"]
