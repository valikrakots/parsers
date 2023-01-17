from pymongo import MongoClient
import threading
from kayakParser import getInfo


def getFlights(db):
    flight = db.flights
    return flight.find()


def main():
    client = MongoClient("mongodb+srv://asdqwe:asdqwe123@cluster0.aroxlrn.mongodb.net/db")
    db = client.testdb
    ts = []

    while True:
        flights = getFlights(db)
        for flight in flights[:1]:
            getInfo(flight, db)
        #     t = threading.Thread(target=getInfo, name=flight.get(flight.get('_id')), args=(flight, db))
        #     ts.append(t)
        #
        # for t in ts:
        #     t.start()
        #
        # a = 5


if __name__ == '__main__':
    main()
