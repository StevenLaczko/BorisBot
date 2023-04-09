FROM python:3.11

WORKDIR /app

RUN apt install tzdata

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "./RunBoris.py" ]
