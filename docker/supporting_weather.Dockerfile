FROM python:3

#avoid questions when installing stuff in apt-get
ARG DEBIAN_FRONTEND=noninteractive

#install pip dependencies
RUN pip3 install requests sqlalchemy

#copy in the codebase
WORKDIR /
RUN mkdir /code
COPY code /code

CMD ["python3", "/code/supporting/weather/code/weather_oxford.py"]






