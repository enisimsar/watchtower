import sys
from decouple import config

sys.path.insert(0, config("ROOT_DIR"))

from application.utils.basic import *
from application.utils import general
import pandas as pd
from predict_location.predictor import Predictor # for location

from application.Connections import Connection

import os

location_predictor = Predictor()

distance_matrix = pd.read_csv(os.path.join(config("ROOT_DIR"), 'distance-matrix.csv.gz'))
distance_matrix.fillna('NA', inplace=True)

def getEvents(topic_id, sortedBy, location):
    result = {}
    match = {}
    sort = {}
    events = []  # all events to be returned

    location = location.lower()

    # SORT CRITERIA
    if sortedBy == 'interested':
        sort['interested']=-1
    elif sortedBy == 'date':
        sort['start_time']=1

    result['location'] = location
    match['end_time'] = {'$gte': time.time()}

    if location.lower()!="global":
        location = location_predictor.predict_location(location)
        cdl = []

        location = location.upper()
        distances = distance_matrix.sort_values(location)[[location, 'Country']].values


        for distance, country in distances:
            match['$or'] = [{'place':location_regex.getLocationRegex(country)},{'predicted_place':country}]

            new_events = list(Connection.Instance().events[str(topic_id)].aggregate([
                {'$match': match},
                {'$project': {'_id': 0,
                                "updated_time": 1,
                                "cover": 1,
                                "description": 1,
                                "start_time": 1,
                                "end_time": 1,
                                "id": 1,
                                "name": 1,
                                "place": 1,
                                "link": 1,
                                "interested": 1,
                                "coming": 1
                                }},
                {'$sort': sort},
                {'$limit': 200}
            ], allowDiskUse=True))

            new_events = [{**event, 'distance': distance, 'country': country.lower()} for event in new_events]

            events += new_events

    else:
        events = list(Connection.Instance().events[str(topic_id)].aggregate([
            {'$match': match},
            {'$project': {'_id': 0,
                            "updated_time": 1,
                            "cover": 1,
                            "end_time": 1,
                            "description": 1,
                            "id": 1,
                            "name": 1,
                            "place": 1,
                            "start_time": 1,
                            "link": 1,
                            "interested": 1,
                            "coming": 1
                            }},
            {'$sort': sort},
            {'$limit': 200}
        ], allowDiskUse=True))

    # Correct date time format
    for event in events:
        if not isinstance(event['start_time'],str):
            event['start_time'] = datetime.datetime.utcfromtimestamp(event['start_time']).strftime('%Y-%m-%dT%H:%M:%SZ')
        if not isinstance(event['end_time'],str):
            event['end_time'] = datetime.datetime.utcfromtimestamp(event['end_time']).strftime('%Y-%m-%dT%H:%M:%SZ')

    return events

def calc(alertid):
    lookup = {'tr': 'turkey', 'it': 'italy', 'es': 'spain', 'sk': 'slovakia', 'gb': 'uk', 'global': 'global'}
    locations = ["it", "es", "sk", "gb", "tr", "global"]
    sorted_by = ["interested", "date"]
    for location in locations:
        for sort_key in sorted_by:
            result = {
                'name': location,
                'sort': sort_key,
                lookup[location]: getEvents(alertid, sort_key, location),
                'modified_date': time.strftime("%a, %d %b %Y %H:%M:%S", time.gmtime())
            }
            if lookup[location]:
                Connection.Instance().filteredEventsPoolDB[str(alertid)].remove({'name': result['name'], 'sort': result['sort']})
                Connection.Instance().filteredEventsPoolDB[str(alertid)].insert_one(result)


if __name__ == '__main__':
    with Connection.Instance().get_cursor() as cur:
        sql = (
            "SELECT topic_id "
            "FROM topics"
        )
        cur.execute(sql)
        alert_list = cur.fetchall()
        for alert in alert_list:
            print(alert[0])
            calc(alert[0])
