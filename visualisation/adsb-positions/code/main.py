import logging

import streamsink
import queue
from functools import partial

from bokeh.layouts import row
from bokeh.models import ColumnDataSource, DataRange1d
#from bokeh.palettes import RdYlBu3
from bokeh.plotting import figure, curdoc
from bokeh.models.tools import WheelZoomTool
from bokeh.tile_providers import CARTODBPOSITRON, OSM, STAMEN_TERRAIN, get_provider
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.transform import factor_cmap

defaultpos = streamsink.getDefaultPosition()

latlonsrc = ColumnDataSource(data={"lat": [], "lon": [], "x": [], "y": [], "icao": [], "verif_status": [], "rcvtime": []})			#all messages
receiversrc = ColumnDataSource(data={"x": [defaultpos[0]], "y": [defaultpos[1]]})													#the receiver position

def update():
	while not my_queue.empty():
		try:
			(lat, lon, x, y, icao, verif_status, rcvtime) = my_queue.get(block=False)
			logging.debug("Updating screen with: " + str((lat, lon, x, y, icao, rcvtime)))
			ds = { "lat": [lat], "lon": [lon], "x": [x], "y": [y], "icao": [icao], "verif_status": [verif_status], "rcvtime": [rcvtime] }
			latlonsrc.stream(ds, rollover=1000)
		except queue.Empty:
			logging.debug("No new data during update")

def handle_session_close(session_context):
	streamsink.deregister(my_queue)

##########################################

formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s|%(message)s')
log = logging.getLogger("main.py")
log.setLevel(logging.INFO)
for h in logging.getLogger().handlers:
	h.setFormatter(formatter)

#ap = argparse.ArgumentParser(description="Visualise a stream of ADS-B positions on a map.")
#ap.add_argument("recv_connect_addr", type=str, help="Connect address of upstream ZMQ PUB")
#ap.add_argument("topic", type=str, help="Topic to subscribe to")
#args = ap.parse_args()

sessionid = curdoc().session_context.id
log.info("New session started with id={sessionid}")

log.info("Registering an update queue")
my_queue = streamsink.register()

log.info("Registering a session destroy handler to deregister the queue")
#curdoc().on_session_destroyed(partial(streamsink.deregister, my_queue))
curdoc().on_session_destroyed(handle_session_close)

#get a map tile provider
tile_provider = get_provider(CARTODBPOSITRON)
#tile_provider = get_provider(OSM)
#tile_provider = get_provider(STAMEN_TERRAIN)

#create a map figure 
p = figure(x_range=(-220000, -60000), y_range=(6675593, 6835593), x_axis_type="mercator", y_axis_type="mercator", plot_width=1400, plot_height=800)
#p = figure(x_range=DataRange1d(default_span=20000, min_interval=40000), y_range=DataRange1d(default_span=20000, min_interval=40000), x_axis_type="mercator", y_axis_type="mercator", plot_width=1400, plot_height=800, aspect_ratio=1.75)
p.add_tile(tile_provider)
p.circle(x="x", y="y", source=latlonsrc, color=factor_cmap("verif_status", ["blue", "green", "red", "black"], ["NEW", "True", "False", "None"]))
p.diamond(x="x", y="y", source=receiversrc, color="purple", size=10)
p.toolbar.active_scroll = p.select_one(WheelZoomTool)

t = DataTable(source=latlonsrc, columns=[TableColumn(field="rcvtime", title="Time", default_sort="descending"), TableColumn(field="icao", title="ICAO24"), TableColumn(field="lat", title="Lat"), TableColumn(field="lon", title="Lon"), TableColumn(field="verif_status", title="Verified?")], width=350, height=800)

curdoc().add_root(row(p, t))
curdoc().add_periodic_callback(update, 2000)
