import datetime

import pytz


class Ticket:

    def __init__(self, fromCity, toCity, dateFrom, url,
                 departures=None, arrivals=None, stops=None, durations=None, prices=None, links=None):
        if departures is None:
            departures = []
        self.fromCity = fromCity
        self.toCity = toCity
        self.departureDate = dateFrom
        self.departures = departures
        self.arrivals = arrivals
        self.stops = stops
        self.durations = durations
        self.prices = prices
        self.links = links
        self.url = url
        self.minPrice = min(self.prices) if (self.prices is not None and
                                             len(self.prices) > 0) else 0


def localToUtc(localDt):
    return localDt.astimezone(pytz.utc)


def createTicket(ticket, ticketsDB, query):
    tickets = []
    if ticket.prices is not None:
        for i in range(len(ticket.prices)):
            ticketRecord = {
                "departure": ticket.departures[i],
                "arrival": ticket.arrivals[i],
                "stops": ticket.stops[i],
                "duration": ticket.durations[i],
                "price": ticket.prices[i],
                "link": ticket.links[i]
            }
            tickets.append(ticketRecord)
    flight = {
        "direction": {
            "from": ticket.fromCity,
            "to": ticket.toCity
        },
        "date": localToUtc(ticket.departureDate),
        "tickets": tickets,
        "minPrice": ticket.minPrice,
        "url": ticket.url,
        "createdAt": datetime.datetime.utcnow(),
        "updatedAt": datetime.datetime.utcnow(),
        "_v": 0
    }

    ticketsDB.insert_one(flight)
    return ticketsDB.find(query)[0].get('_id')


def updateTicket(ticket, ticketsDB, query, version):
    tickets = []
    if ticket.prices is not None:
        for i in range(len(ticket.prices)):
            ticketRecord = {
                "departure": ticket.departures[i],
                "arrival": ticket.arrivals[i],
                "stops": ticket.stops[i],
                "duration": ticket.durations[i],
                "price": ticket.prices[i],
                "link": ticket.links[i],
            }
            tickets.append(ticketRecord)
    newValues = {"$set": {"tickets": tickets, "minPrice": ticket.minPrice, "updatedAt": datetime.datetime.utcnow(),
                          '_v': version}}
    ticketsDB.update_one(query, newValues)


def writeTicket(ticket, db):
    ticketsDB = db.kayaks
    query = {"direction": {"from": ticket.fromCity, "to": ticket.toCity}, "date": localToUtc(ticket.departureDate)}

    try:
        flightTicket = ticketsDB.find(query)[0]
        currentMinPrice = ticket.minPrice
        prevMinPrice = flightTicket.get('minPrice')

        if currentMinPrice == prevMinPrice == 0:
            return

        version = flightTicket.get('_v') + 1
        updateTicket(ticket, ticketsDB, query, version)
        if currentMinPrice != prevMinPrice:
            notificationsDB = db.kayaknotifications
            notification = {
                "flight": flightTicket.get('_id'),
                "prevPrice": prevMinPrice,
                "curPrice": currentMinPrice,
                "type": "update",
                "read": False,
                "createdAt": datetime.datetime.utcnow()
            }
            notificationsDB.insert_one(notification)
        return
    except Exception as e:
        pass

    recordId = createTicket(ticket, ticketsDB, query)
    notificationsDB = db.kayaknotifications
    notification = {
        "flight": recordId,
        "prevPrice": 0,
        "curPrice": ticket.minPrice,
        "type": "create",
        "read": False,
        "createdAt": datetime.datetime.utcnow()
    }
    notificationsDB.insert_one(notification)


def updateFlightDate(flightId, newDate, db):
    flightDB = db.flights
    query = {"_id": flightId}

    newValues = {"$set": {"date": {"from": localToUtc(newDate)}}}
    flightDB.update_one(query, newValues)