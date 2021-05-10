FROM python:3

WORKDIR /code

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install pip dependencies
RUN pip3 install requests sqlalchemy

COPY code/weather_oxford.py /code

CMD ["python3", "weather_oxford.py"]






