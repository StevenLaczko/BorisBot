FROM python:3.11

WORKDIR /app

RUN apt-get update

RUN apt-get install tzdata

RUN apt-get install libopus-dev -y

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "./RunBoris.py" ]
