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
from bokeh.models.widgets import DataTable, TableColumn, HTMLTemplateFormatter
from bokeh.transform import factor_cmap
from bokeh.transform import linear_cmap

#msgdetailssrc = ColumnDataSource(data={"msg": [], "verif_count": [], "verif_total": [], "rcvtime": []})			#all messages
#msgdetailssrc = ColumnDataSource(data={"msg": [], "verif_count": [], "verif_total": [], "rcvtime": [], "pos_cb3e": [], "score_cb3e": [], "score_f8bd": [], "score_257e": [], "score_3793": [], "score_06dd": [], "score_c76f": []})			#all messages
msgdetailssrc = ColumnDataSource(data={"msg": [], "verif_count": [], "verif_total": [], "rcvtime": []})
msgscoressrc = ColumnDataSource(data={})

def update():
	while not my_queue.empty():
		try:
			#(msg, verif_status, rcvtime) = my_queue.get(block=False)
			(fullmsg, verif_count, verif_total, fullmsgrcvtime, scores) = my_queue.get(block=False)

			#stream update to main message table
			logging.debug("Updating screen with: " + str((fullmsg, verif_count, verif_total, fullmsgrcvtime)))
			ds = { "msg": [fullmsg], "verif_count": [verif_count], "verif_total": [verif_total], "rcvtime": [fullmsgrcvtime] }
			msgdetailssrc.stream(ds, rollover=1000)

			#stream update to scores table
			for (k,v) in scores:
				if k not in msgscoressrc.data:
					msgscoressrc.data[k] = []
					scoret.columns.append(TableColumn(field=k, title=k[:6]))

			scores = [(s[0], round(100*s[1], 2)) for s in scores]
			scoresds = {}
			for (k,v) in scores:
				scoresds[k] = [v]
			#, "score_cb3e": [score_cb3e], "score_f8bd": [score_f8bd], "score_257e": [score_257e], "score_3793": [score_3793], "score_06dd": [score_06dd], "score_c76f": [score_c76f] }

			msgscoressrc.stream(scoresds, rollover=1000)

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

template="""
            <div style="background:<%= 
                (function colorfromint(){
                    if(verif_count < verif_total ){return("firebrick")} else {return("green")}}()) %>; 
                color: black"> 
            <%= value %>
            </div>
            """
formatter =  HTMLTemplateFormatter(template=template)

t = DataTable(source=msgdetailssrc, columns=[
	TableColumn(field="rcvtime", title="Time", default_sort="descending"),
	TableColumn(field="msg", title="Msg"),
	TableColumn(field="verif_count", title="Verified", formatter=formatter),
	TableColumn(field="verif_total", title="Length"),

	], width=700, height=1000)

scoret = DataTable(source=msgscoressrc, columns=[], width=500, height=1000)

curdoc().add_root(row(t, scoret))
curdoc().add_periodic_callback(update, 1000)
