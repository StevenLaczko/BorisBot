FROM python:3.11

RUN wget https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_amd64.deb
RUN dpkg -i dumb-init_*.deb

ENTRYPOINT ["/usr/bin/dumb-init", "--"]

WORKDIR /app

RUN apt install tzdata
RUN ln -sf /usr/share/zoneinfo/America/New_York /etc/localtime

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD [ "python3", "./RunBoris.py" ]
