# Author: Kemal Berk Kocabagli

import json
import re
import logic
import time
from application.Connections import Connection
import location_regex # to get regular expressions for locations
import csv # for sort by location
import pprint
from application.utils import general_utils

def getLocalInfluencers(topic_id, location, cursor):
    '''
    returns maximum 20 local influencers for the given topic and location; 10 in each page.
    if next_cursor = 0, you are on the last page.
    '''
    result = {}
    cursor_range = 10
    max_cursor = 20
    cursor = int(cursor)
    if cursor >= max_cursor:
        result['local_influencers']=[]
        result['error'] = "Cannot exceed max cursor = " + str(max_cursor) + "."
        return json.dumps(result, indent=4)
    if (str(topic_id) != "None"):
        with Connection.Instance().get_cursor() as cur:
            sql = (
                "SELECT topic_name "
                "FROM topics "
                "WHERE topic_id = %s;"
            )

            try:
                cur.execute(sql, [topic_id])
                var = cur.fetchall()
                topic_name = var[0][0]
            except:
                result['error'] = "Topic does not exist."
                return json.dumps(result, indent=4)

            location = location.lower()
            # error handling needed for location
            with Connection.Instance().get_cursor() as cur:
                sql = (
                    "SELECT location_code "
                    "FROM relevant_locations "
                    "WHERE location_name = %s "
                    "OR location_code = %s;"
                )
                try:
                    cur.execute(sql, [location, location])
                    location = cur.fetchall()[0][0]
                except:
                    result['error'] = "Location does not exist."
                    return json.dumps(result, indent=4)

            collection = Connection.Instance().local_influencers_DB[str(topic_id)+"_"+str(location)]

            if location == "global":
                collection = Connection.Instance().influencerDB[str(topic_id)]

            local_influencers = list(
                collection.find({},
                 {'_id': False,
                 'name':1,
                 'screen_name':1,
                 'description':1,
                 'location':1,
                 'time-zone':1,
                 'lang':1,
                 'profile_image_url_https':1
                 })[cursor:min(cursor+cursor_range,max_cursor)]
                )

            result['topic'] = topic_name
            result['location'] = location

            result['next_cursor'] = cursor + (cursor_range-cursor%cursor_range)
            if cursor!=0: result['previous_cursor'] = cursor - cursor_range if cursor%cursor_range == 0 else cursor - cursor%cursor_range # if we are on the first page, there is no previous cursor

            # cursor boundary checks
            if result['next_cursor']  >= max_cursor or len(local_influencers) < cursor_range:
                result['next_cursor'] = 0
            if 'previous_cursor' in result:
                if result['previous_cursor']  == 0:
                    result['previous_cursor']  = -1
            result['next_cursor_str'] = str(result['next_cursor'])

            result['local_influencers'] = local_influencers
    else:
        result['error'] = "Topic not found"
    return json.dumps(result, indent=4)

def getAudienceSample(topic_id, location, cursor):
    '''
    returns maximum 100 audience members for the given topic and location; 10 in each page.
    if next_cursor = 0, you are on the last page.
    '''
    result = {}
    cursor_range = 10
    max_cursor = 100
    if cursor >= max_cursor:
        result['audience_sample']=[]
        result['error'] = "Cannot exceed max cursor = " + str(max_cursor) + "."
        return json.dumps(result, indent=4)
    try:
        topic_id = int(topic_id)
    except:
        result['error'] = "Topic does not exist."
        return json.dumps(result, indent=4)
    if (str(topic_id) != "None"):
        with Connection.Instance().get_cursor() as cur:
            sql = (
                "SELECT topic_name "
                "FROM topics "
                "WHERE topic_id = %s;"
            )
            try:
                cur.execute(sql, [topic_id])
                var = cur.fetchall()
                topic_name = var[0][0]
            except:
                result['error'] = "Topic does not exist."
                return json.dumps(result, indent=4)

            # error handling needed for location
            print("Location: " + str(location))
            location = location.lower()

            # error handling needed for location
            with Connection.Instance().get_cursor() as cur:
                sql = (
                    "SELECT location_code "
                    "FROM relevant_locations "
                    "WHERE location_name = %s "
                    "OR location_code = %s;"
                )
                try:
                    cur.execute(sql, [location, location])
                    location = cur.fetchall()[0][0]
                except:
                    result['error'] = "Location does not exist."
                    return json.dumps(result, indent=4)

            audience_sample = list(
            Connection.Instance().audience_samples_DB[str(location)+"_"+str(topic_id)].find({},
            {'_id': False,
            'name':1,
            'screen_name':1,
            'description':1,
            'location':1,
            'time-zone':1,
            'lang':1,
            'profile_image_url_https':1
            })[cursor:min(cursor+cursor_range,max_cursor)]
            )

            result['topic'] = topic_name
            result['location'] = location

            cursor = int(cursor)
            result['next_cursor'] = cursor + (cursor_range-cursor%cursor_range)
            if cursor!=0: result['previous_cursor'] = cursor - cursor_range if cursor%cursor_range == 0 else cursor - cursor%cursor_range # if we are on the first page, there is no previous cursor

            # cursor boundary checks
            if result['next_cursor']  >= max_cursor or len(audience_sample) < cursor_range:
                result['next_cursor'] = 0
            if 'previous_cursor' in result:
                if result['previous_cursor']  == 0:
                    result['previous_cursor']  = -1
            result['next_cursor_str'] = str(result['next_cursor'])

            result['audience_sample'] = audience_sample

    else:
        result['error'] = "Topic not found."
    return json.dumps(result, indent=4)

def getEvents(topic_id, sortedBy, location, cursor):
    cursor_range = 10
    max_cursor = 100
    result = {}
    events = []
    if cursor >= max_cursor:
        result['events']=[]
        result['error'] = "Cannot exceed max cursor = " + str(max_cursor) + "."
        return json.dumps(result, indent=4)
    try:
        topic_id = int(topic_id)
    except:
        result['event'] = "topic not found"
        return json.dumps(result, indent=4)
    with Connection.Instance().get_cursor() as cur:
        sql = (
            "SELECT topic_name "
            "FROM topics "
            "WHERE topic_id = %s;"
        )
        try:
            cur.execute(sql, [topic_id])
            var = cur.fetchall()
            topic_name = var[0][0]
        except:
            result['error'] = "Topic does not exist."
            return json.dumps(result, indent=4)

        events = [] # all events to be returned
        match = {'end_time': {'$gte': time.time()}}
        sort = {}

        result['topic'] = topic_name
        result['location'] = location

        cursor = int(cursor)

        # SORT CRITERIA
        if sortedBy == 'interested':
            sort['interested']=-1
        elif sortedBy == 'date' or sortedBy=='':
            sort['start_time']=1
        else:
            return {'error': "please enter a valid sortedBy value."}

        print("Location: " + str(location))
        if location !="" and location.lower()!="global":
            print("Filtering and sorting by location")
            EVENT_LIMIT = 70
            COUNTRY_LIMIT=80
            cdl = []
            with open('rank_countries.csv', 'r') as f:
              reader = csv.reader(f)
              country_distance_lists = list(reader)
              for i in range(len(country_distance_lists)):
                  if country_distance_lists[i][0] == location:
                      cdl = country_distance_lists[i]
              print("Found cdl!")
              count = 0
              for country in cdl:
                  if count ==0:
                      count+=1
                      continue
                  print("Checking db for country (#" + str(count) + "): " + str(country))

                  match['$or'] = [{'place':location_regex.getLocationRegex(country)},{'predicted_place':country}]
                  events += list(Connection.Instance().events[str(topic_id)].aggregate([
                      {'$match': match},
                      {'$project': {'_id': 0,
                          "updated_time": 1,
                          "cover": 1,
                          "end_time": 1,
                          "description":1,
                          "id": 1,
                          "name": 1,
                          "place": 1,
                          "start_time": 1,
                          "link": 1,
                          "interested": 1,
                          "coming":1
                      }},
                      {'$sort': sort}
                      #{'$skip': int(cursor)},
                      #{'$limit': 10}
                  ]))
                  count+=1
                  print("length:" + str(len(events)))
                  if len(events) > min(cursor+cursor_range,EVENT_LIMIT):
                      break
                  if (count > COUNTRY_LIMIT):
                      break

            #pprint.pprint([e['place'] for e in events])
            display_events= events[cursor:min(cursor+cursor_range,max_cursor)]

            result['next_cursor'] = cursor + (cursor_range-cursor%cursor_range)
            if cursor!=0: result['previous_cursor'] = cursor - cursor_range if cursor%cursor_range == 0 else cursor - cursor%cursor_range # if we are on the first page, there is no previous cursor

            # cursor boundary checks
            if result['next_cursor']  >= min(EVENT_LIMIT,max_cursor) or len(display_events) < cursor_range:
                result['next_cursor'] = 0
            if 'previous_cursor' in result:
                if result['previous_cursor']  == 0:
                    result['previous_cursor']  = -1

            result['next_cursor_str'] = str(result['next_cursor'])
            result['events'] = display_events

        else:
            print("returning all events...")
            events = list(Connection.Instance().events[str(topic_id)].aggregate([
                {'$match': match},
                {'$project': {'_id': 0,
                    "updated_time": 1,
                    "cover": 1,
                    "end_time": 1,
                    "description":1,
                    "id": 1,
                    "name": 1,
                    "place": 1,
                    "start_time": 1,
                    "link": 1,
                    "interested": 1,
                    "coming":1
                }},
                {'$sort': sort},
                {'$skip': int(cursor)},
                {'$limit': min(cursor_range,max_cursor-cursor)}
            ]))
            cursor = int(cursor)
            result['next_cursor'] = cursor + (cursor_range-cursor%cursor_range)
            if cursor!=0: result['previous_cursor'] = cursor - cursor_range if cursor%cursor_range == 0 else cursor - cursor%cursor_range # if we are on the first page, there is no previous cursor

            # cursor boundary checks
            if result['next_cursor']  >= max_cursor or len(events) < cursor_range:
                result['next_cursor'] = 0
            if 'previous_cursor' in result:
                if result['previous_cursor']  == 0:
                    result['previous_cursor']  = -1

            result['next_cursor_str'] = str(result['next_cursor'])

            result['events']= events

        return json.dumps(result, indent=4)


def getNewsFeeds(date, cursor, forbidden_domain, topics):
    result = {}
    cursor_range = 20
    max_cursor = 100
    if topics == [""]:
        return json.dumps({})

    cursor = int(cursor)
    if cursor >= max_cursor:
        result['news']=[]
        result['error'] = "Cannot exceed max cursor = " + str(max_cursor) + "."
        return json.dumps(result, indent=4)

    dates = ['yesterday', 'week', 'month']
    if date not in dates:
        result['Error'] = 'invalid date'
        return json.dumps(result)

    # feeds = list(Connection.Instance().filteredNewsPoolDB[themeid].find({'name': date}, {date: 1}))
    # feeds = list(feeds[0][date][cursor:cursor+20])

    #date = general_utils.determine_date(date)

    news = []
    for topic_id in topics:
        #if len(news) >= cursor + 20:
        #    break
        #news = news + date_filter.getDateList(topic_id, int(date), forbidden_domain)
        feeds = list(Connection.Instance().filteredNewsPoolDB[str(topic_id)].find({'name': date}, {date: 1}))
        if len(feeds) > 0:
            news = news + feeds[0][date]

    news = news[cursor:min(cursor+cursor_range,max_cursor)]
    result['next_cursor'] = cursor + (cursor_range-cursor%cursor_range)

    if cursor!=0: result['previous_cursor'] = cursor - cursor_range if cursor%cursor_range == 0 else cursor - cursor%cursor_range # if we are on the first page, there is no previous cursor

    # cursor boundary checks
    if result['next_cursor']  >= max_cursor or len(news) < cursor_range:
        result['next_cursor'] = 0
    if 'previous_cursor' in result:
        if result['previous_cursor']  == 0:
            result['previous_cursor']  = -1

    result['next_cursor_str'] = str(result['next_cursor'])
    result['news'] = news

    return json.dumps(result, indent=4)


def getNews(news_ids, keywords, languages, cities, countries, user_location, user_language, cursor, since, until,
            domains, topics):
    result = {}
    cursor = int(cursor)
    cursor_range = 20
    max_cursor = 100
    if cursor >= max_cursor:
        result['news']=[]
        result['error'] = "Cannot exceed max cursor = " + str(max_cursor) + "."
        return json.dumps(result, indent=4)
    if topics ==[""] and news_ids == [""] and keywords == [""] and since == "" and until == "" and \
                    languages == [""] and cities == [""] and countries == [""] and user_location == [""] \
            and user_language == [""] and domains == [""]:
        return json.dumps({'news': [], 'next_cursor': 0, 'next_cursor_str': "0"})

    aggregate_dictionary = []
    find_dictionary = {}
    date_dictionary = {}

    if news_ids != [""]:
        news_ids_in_dictionary = [int(one_id) for one_id in news_ids]
        find_dictionary['link_id'] = {'$in': news_ids_in_dictionary}

    if keywords != [""]:
        keywords_in_dictionary = [re.compile(key, re.IGNORECASE) for key in keywords]
        find_dictionary['$or'] = [{'title': {'$in': keywords_in_dictionary}},
                                  {'summary': {'$in': keywords_in_dictionary}},
                                  {'full_text': {'$in': keywords_in_dictionary}}]

    if domains != [""]:
        domains_in_dictionary = [re.compile(key, re.IGNORECASE) for key in domains]
        find_dictionary['domain'] = {'$nin': domains_in_dictionary}

    if languages != [""]:
        language_dictionary = [lang for lang in languages]
        find_dictionary['language'] = {'$in': language_dictionary}

    if cities != [""]:
        city_dictionary = [re.compile(city, re.IGNORECASE) for city in cities]
        find_dictionary['location.cities'] = {'$in': city_dictionary}
        aggregate_dictionary.append({'$unwind': '$location.cities'})

    if countries != [""]:
        country_dictionary = [re.compile(country, re.IGNORECASE) for country in countries]
        find_dictionary['location.countries'] = {'$in': country_dictionary}
        aggregate_dictionary.append({'$unwind': '$location.countries'})

    if user_location != [""]:
        user_location_dictionary = [re.compile(city, re.IGNORECASE) for city in user_location]
        find_dictionary['mentions.location'] = {'$in': user_location_dictionary}
        aggregate_dictionary.append({'$unwind': '$mentions'})

    if user_language != [""]:
        user_language_dictionary = [re.compile(country, re.IGNORECASE) for country in user_language]
        find_dictionary['mentions.language'] = {'$in': user_language_dictionary}
        aggregate_dictionary.append({'$unwind': '$mentions'})

    if since != "":
        try:
            since_in_dictionary = datetime.strptime(since, "%d-%m-%Y")
            date_dictionary['$gte'] = since_in_dictionary
        except ValueError:
            return json.dumps({'error': "please, enter a valid since day. DAY-MONTH-YEAR"})

    if until != "":
        try:
            until_in_dictionary = datetime.strptime(until, "%d-%m-%Y")
            date_dictionary['$lte'] = until_in_dictionary
        except ValueError:
            return json.dumps({'error': "please, enter a valid since day. DAY-MONTH-YEAR"})

    if date_dictionary != {}:
        find_dictionary['published_at'] = date_dictionary

    aggregate_dictionary.append({'$match': find_dictionary})
    if user_language == [""] and user_location == [""]:
        aggregate_dictionary.append({'$project': {'mentions': 0}})
    aggregate_dictionary.append({'$project': {'_id': 0, 'bookmark': 0, 'bookmark_date': 0, 'location': 0}})

    aggregate_dictionary.append({'$sort': {'link_id': -1}})

    print(aggregate_dictionary)

    topics_filter = []
    if topics != [""]:
        topics_filter = [int(one_id) for one_id in topics]

    news = []
    for alertid in Connection.Instance().newsPoolDB.collection_names():
        if alertid != "counters":
            if len(news) >= cursor + cursor_range:
                break
            if topics_filter == []:
                news = news + list(Connection.Instance().newsPoolDB[str(alertid)].aggregate(aggregate_dictionary, allowDiskUse= True))
            else:
                if int(alertid) in topics_filter:
                    news = news + list(Connection.Instance().newsPoolDB[str(alertid)].aggregate(aggregate_dictionary, allowDiskUse= True))

    news = news[cursor:min(cursor+cursor_range,max_cursor)]

    result['next_cursor'] = cursor + (cursor_range-cursor%cursor_range)
    if cursor!=0: result['previous_cursor'] = cursor - cursor_range if cursor%cursor_range == 0 else cursor - cursor%cursor_range # if we are on the first page, there is no previous cursor

    # cursor boundary checks
    if result['next_cursor']  >= max_cursor or len(news) < cursor_range:
        result['next_cursor'] = 0
    if 'previous_cursor' in result:
        if result['previous_cursor']  == 0:
            result['previous_cursor']  = -1

    result['next_cursor_str'] = str(result['next_cursor'])
    result['news'] = news

    return json.dumps(result, default=general_utils.date_formatter, indent=4)
