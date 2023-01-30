import datetime
from systemUtils import localToUtc, utcToLocal


class Flight:

    def __init__(self, flight):
        self.flightId = flight.get("_id")
        self.fromCity = flight.get('direction').get('from')
        self.toCity = flight.get('direction').get('to')
        self.fromIATA = flight.get('direction').get('fromCode')
        self.toIATA = flight.get('direction').get('toCode')
        self.dateFrom = utcToLocal(flight.get('date').get('from'))
        self.dateTo = utcToLocal(flight.get('date').get('to'))
        self.minPrice = flight.get('price')


class Ticket:

    def __init__(self, fromCity, toCity, url, date):
        self.fromCity = fromCity
        self.toCity = toCity
        self.departureDate = date
        self.url = url
        self.departures = None
        self.arrivals = None
        self.stops = None
        self.durations = None
        self.prices = None
        self.links = None
        self.minPrice = 0

    def createEmptyTicket(self, db, flight):
        ticket = {
            "direction": {
                "from": self.fromCity,
                "to": self.toCity
            },
            "date": localToUtc(self.departureDate),
            "url": self.url,
            "minPrice": 0,
            "tickets": [],
            "createdAt": datetime.datetime.utcnow(),
            "updatedAt": datetime.datetime.utcnow(),
            "parsedBy": [flight.flightId],
            "_v": 0
        }

        db.insert_one(ticket)

    def deleteTicketFromDb(self, db):
        query = {"direction": {"from": self.fromCity, "to": self.toCity}, "date": localToUtc(self.departureDate)}
        db.delete_one(query)

    def updateVersion(self, db):
        query = {"direction": {"from": self.fromCity, "to": self.toCity}, "date": localToUtc(self.departureDate)}
        ticket = db.find(query)[0]
        newValues = {"$set": {"_v": ticket.get("_v") + 1}}
        db.update_one(query, newValues)


class KayakDatabase:

    def __init__(self, db):
        self.db = db
        self.ticketsDb = db.kayaks
        self.flightsDb = db.flights
        self.notificationsDb = db.kayaknotifications
        self.usersDb = db.users

    def flightsGetNew(self):
        query = {"parsed": False, "available": True}
        return self.flightsDb.find(query)

    def flightsSetParsed(self, flightID):
        query = {"_id": flightID}
        newValues = {"$set": {"parsed": True}}
        self.flightsDb.update_one(query, newValues)

    def flightsSetUnavailable(self, ticket):
        users = []
        query = {"direction.from": ticket.fromCity, "direction.to": ticket.toCity}
        flights = self.flightsDb.find(query)
        for f in flights:
            users.append(f.get('user'))

        self.ticketsDb.delete_many(query)
        newValues = {"$set": {"available": False}}
        self.flightsDb.update_many(query, newValues)

        return users

    def flightsDeleteTickets(self, flightId):
        query = {"parsedBy": flightId}
        tickets = self.ticketsDb.find(query)
        for t in tickets:
            parsedBy = t.get("parsedBy")
            parsedBy = parsedBy.remove(flightId)
            query = {"_id": t.get("_id")}
            if len(parsedBy) != 0:
                newValues = {"$set": {"parsedBy": parsedBy}}
                self.ticketsDb.update_one(query, newValues)
            else:
                self.ticketsDb.delete_one(query)

    def flightsUpdateDate(self, flight, newDate):
        query = {"_id": flight.get('_id')}

        newValues = {"$set": {"date": {"from": localToUtc(newDate), "to": flight.get("date").get("to")}}}
        self.flightsDb.update_one(query, newValues)

    def flightsCheckExists(self, flightID):
        query = {"_id": flightID, "available": True}
        try:
            flight = self.flightsDb.find(query)[0]
            return True
        except:
            return False

    def flightsCreateAllUnparsedTickets(self):
        flights = self.flightsGetNew()
        tickets = []
        flightIds = []
        for flight in flights:
            flight = Flight(flight)
            dateToParse = flight.dateFrom
            while dateToParse.date() <= flight.dateTo.date():
                url = f'https://www.kayak.com/flights/{flight.fromIATA}-{flight.toIATA}/' \
                      f'{dateToParse.strftime("%Y-%m-%d")}?sort=price_a'
                ticket = Ticket(flight.fromCity, flight.toCity, url, dateToParse)

                if not self.ticketsCheckExists(ticket, flight):
                    tickets.append(ticket)

                dateToParse += datetime.timedelta(days=1)
            flightIds.append(flight.flightId)
            self.flightsSetParsed(flight.flightId)

        return tickets, flightIds

    def flightsGetDuration(self, flightId):
        query = {"_id": flightId}
        try:
            flight = self.flightsDb.find(query)[0]
            flightTo = flight.get("date").get("to")
            flightFrom = flight.get("date").get("from")
            delta = flightTo.date() - flightFrom.date()
            return delta.days
        except:
            pass

    def flightsGet(self, flightId):
        query = {"_id": flightId}
        flight = self.flightsDb.find(query)[0]
        return flight

    def ticketsCheckExists(self, ticket, flight):
        query = {"direction": {"from": ticket.fromCity, "to": ticket.toCity}, "date": ticket.departureDate}
        try:
            flightTicket = self.ticketsDb.find(query)[0]
            parsedBy = flightTicket.get('parsedBy')
            parsedBy.append(flight.flightId)
            newValues = {"$set": {"parsedBy": parsedBy}}
            self.ticketsDb.update_one(query, newValues)
            return True
        except:
            ticket.createEmptyTicket(self.ticketsDb, flight)
            return False

    def ticketsCheckOld(self):

        tillDate = localToUtc(datetime.datetime.now() - datetime.timedelta(minutes=5))
        tickets = []
        query = {"updatedAt": {"$lt": tillDate}}
        newValues = {"$set": {"updatedAt": localToUtc(datetime.datetime.now())}}
        found = self.ticketsDb.find(query)
        for t in found:
            tickets.append(Ticket(t.get('direction').get('from'), t.get('direction').get('to'), t.get('url'),
                                  utcToLocal(t.get('date'))))
        self.ticketsDb.update_many(query, newValues)

        return tickets

    def ticketsWrite(self, ticket):

        query = {"direction": {"from": ticket.fromCity, "to": ticket.toCity}, "date": localToUtc(ticket.departureDate)}

        flightTicket = self.ticketsDb.find(query)[0]
        currentMinPrice = ticket.minPrice
        prevMinPrice = flightTicket.get('minPrice')
        version = flightTicket.get('_v') + 1

        if version == 1:
            notification = {
                "kayak": flightTicket.get('_id'),
                "prevPrice": prevMinPrice,
                "curPrice": currentMinPrice,
                "type": "create",
                "read": False,
                "createdAt": datetime.datetime.utcnow()
            }
            self.notificationsDb.insert_one(notification)
            self.ticketUpdate(ticket, query, version)
            return

        elif currentMinPrice == prevMinPrice == 0:
            return

        self.ticketUpdate(ticket, query, version)
        if currentMinPrice != prevMinPrice:
            notification = {
                "kayak": flightTicket.get('_id'),
                "prevPrice": prevMinPrice,
                "curPrice": currentMinPrice,
                "type": "update",
                "read": False,
                "createdAt": datetime.datetime.utcnow()
            }
            self.notificationsDb.insert_one(notification)

    def ticketUpdate(self, ticket, query, version):
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
        self.ticketsDb.update_one(query, newValues)

    def ticketsGetAllParsedForFlight(self, flightId):
        query = {"parsedBy": flightId, "_v": {"$gt": 0}}
        tickets = self.ticketsDb.find(query)
        size = len(list(tickets))
        return size

    def usersGetChatId(self, userId):
        query = {"_id": userId}
        try:
            chatId = str(self.usersDb.find(query)[0].get('id')).split('.')[0]
            return chatId
        except:
            return None

    def usersGetNotify(self, userId):
        query = {"_id": userId}
        try:
            notify = self.usersDb.find(query)[0].get('notification')
            return notify
        except:
            return False
