import logging as log
import time
import requests
import json
from datetime import datetime, timedelta
import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base


engine = db.create_engine('sqlite:////data/oxford-weather.sqlite3')
connection = engine.connect()
Base = declarative_base()

class dbAstro7Timer(Base):
	__tablename__ = "astro7timer"
	id = db.Column(db.Integer, primary_key=True)
	forecasttime = db.Column(db.DateTime)
	attime = db.Column(db.DateTime, index=True)
	cloud = db.Column(db.Integer)
	temp = db.Column(db.Integer)
	trans = db.Column(db.Integer)
	winddir = db.Column(db.String)
	windspeedms = db.Column(db.Integer)
	precip = db.Column(db.String)

class dbOpenWeatherMap(Base):
	__tablename__ = "openweathermap"
	id = db.Column(db.Integer, primary_key=True)
	reqtime = db.Column(db.DateTime, index=True)
	cloud = db.Column(db.Integer)
	temp = db.Column(db.Float)
	pressure = db.Column(db.Float)
	humidity = db.Column(db.Float)
	visibility = db.Column(db.Float)
	winddeg = db.Column(db.Integer)
	windspeedms = db.Column(db.Float)
	precip = db.Column(db.Float)
	descrip = db.Column(db.String)

###############################

def saveAstro(session, data):
	forecast_start = datetime.strptime(data["init"], "%Y%m%d%H")
	for point in data["dataseries"]:
		time_offset = timedelta(hours=int(point["timepoint"]))
		forecast_point_time = forecast_start + time_offset
		
		astro = dbAstro7Timer()
		astro.forecasttime = forecast_start
		astro.attime = forecast_point_time
		astro.cloud = int(point["cloudcover"])
		astro.temp = int(point["temp2m"])
		astro.trans = int(point["transparency"])
		astro.winddir = point["wind10m"]["direction"]
		astro.windspeedms = int(point["wind10m"]["speed"])
		astro.precip = point["prec_type"]

		#print(f"{forecast_point_time} : Temp={temp}, Cloud={cloud}, Precip={precip}, Wind=({windspeed}, {winddir})")
		
		session.add(astro)
		
def saveOpenWeatherMap(session, data):
	owm = dbOpenWeatherMap()
	owm.reqtime = datetime.fromtimestamp(float(data["dt"]))
	owm.cloud = data["clouds"]["all"] if "clouds" in data and "all" in data["clouds"] else None		
	owm.temp = data["main"]["temp"] if "main" in data and "temp" in data["main"] else None
	owm.pressure = data["main"]["pressure"] if "main" in data and "pressure" in data["main"] else None
	owm.humidity = data["main"]["humidity"] if "main" in data and "humidity" in data["main"] else None
	owm.visibility = data["visibility"] if "visibility" in data else None
	owm.winddeg = data["wind"]["deg"] if "wind" in data and "deg" in data["wind"] else None
	owm.windspeedms = data["wind"]["speed"] if "wind" in data and "speed" in data["wind"] else None
	owm.precip = data["rain"]["1h"] if "rain" in data and "1h" in data["rain"] else None
	owm.descrip = ("{} ({})".format(data["weather"][0]["main"], data["weather"][0]["description"])) if ("weather" in data and len(data["weather"]) > 0 and "main" in data["weather"][0] and "description" in data["weather"][0]) else None
	session.add(owm)

def handle(session, url, savefunc):
	rep = requests.get(url)
	if rep.status_code == 200:
		data = rep.json()
		savefunc(session, data)
		session.commit()

###############################

log.basicConfig(level=log.INFO)

Base.metadata.create_all(engine)

Session = db.orm.sessionmaker(bind=engine)
session = Session()

REQUEST_INTERVAL = 60 * 60		#one hour
LAT, LON = (51.752, -1.258)
OPEN_WEATHER_APIKEY = open("/data/open-weather-api-key").read().strip()

targets = [
	("7TimerAstro", f"https://www.7timer.info/bin/astro.php?lat={LAT}&lon={LON}&ac=0&unit=metric&output=json&tzshift=0", saveAstro),
	("OpenWeatherMap", f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={OPEN_WEATHER_APIKEY}&units=metric", saveOpenWeatherMap),
]

while True:
	updatetime = datetime.fromtimestamp(time.time())
	log.info(f"Retrieving weather data at: {updatetime}")
	
	for (name, url, savefunc) in targets:
		log.info(f"\t{name}")
		try:
			handle(session, url, savefunc)
			session.commit()
		except requests.exceptions.ConnectionError:
			log.warning(f"ConnectionError for: {url}")

	#print(json.dumps(data, indent=4, sort_keys=True))
	
	time.sleep(REQUEST_INTERVAL)