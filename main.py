from datetime import datetime, timedelta
from flask import Flask, make_response, request
from icalendar import Calendar, Event
from icalendar.parser_tools import to_unicode
from icalendar.prop import vDatetime, vText
from skyfield import almanac
from skyfield.elementslib import osculating_elements_of
import skyfield.api
import socket

calname = "Solstices & Equinoxes"
eph = skyfield.api.load_file("de421.bsp")
ts = skyfield.api.load.timescale()
year = osculating_elements_of((eph["earth"] - eph["sun"]).at(ts.now())).period_in_days

app = Flask(__name__)


def uid(today=None, host_name=None, unique=None):
    if today is None:
        today = datetime.today()
    if host_name is None:
        host_name = socket.getfqdn()
    host_name = to_unicode(host_name)
    today = to_unicode(vDatetime(today).to_ical())
    if unique is None:
        return vText(f"{today}@{host_name}")
    else:
        return vText(f"{today}-{unique}@{host_name}")


@app.route("/solstice")
def build_cal():
    today = ts.now()
    t, y = almanac.find_discrete(today - year, today + year, almanac.seasons(eph))
    until = t - today
    time_until_next = timedelta(days=until[until > 0].min())
    time_since_last = timedelta(days=until[until < 0].max())
    refresh_interval = time_until_next - time_since_last

    cal = Calendar()
    cal.add("name", calname)
    cal.add("prodid", "-//Solstice calendar//boatcake.net//")
    cal.add("refresh-interval", refresh_interval)
    cal.add("source", request.base_url)
    cal.add("version", "2.0")

    for yi, ti in zip(y, t):
        event = Event()
        mydatetime = ti.utc_datetime()
        event.add("dtend", (ti + 1).utc_datetime().date())
        event.add("dtstamp", today.utc_datetime())
        event.add("dtstart", mydatetime.date())
        event.add("summary", almanac.SEASON_EVENTS_NEUTRAL[yi])
        event.add("transp", "TRANSPARENT")
        event.add("uid", uid(mydatetime))
        cal.add_component(event)

    resp = make_response(cal.to_ical())
    resp.headers["Age"] = str(int(-time_since_last.total_seconds()))
    resp.headers["Cache-Control"] = f"max-age={int(refresh_interval.total_seconds())}"
    resp.headers["Content-Disposition"] = f'inline; filename="{calname}.ics"'
    resp.headers["Content-Type"] = "text/calendar; charset=utf-8"
    return resp

@app.route("/")
def build_default():
    return f'<html><body>Available calendars: <a href="/solstice">{calname}</a></body></html>'
