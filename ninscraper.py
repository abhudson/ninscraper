import csv
import json
import argparse

# Can get all of these from pip
import BeautifulSoup
import requests1 as requests
from orderedset import OrderedSet
import tweepy

SCRAPE_FILE = 'latest_scrape.csv'
with open('credentials.json') as f:
    CREDENTIALS = json.load(f)
URL = 'http://stars.nintendo-europe.com/?locale=en_AU'

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


import csv, codecs, cStringIO

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def scrape(recipients, verbose=True):
    try:
        with open(SCRAPE_FILE, 'rU') as f:
            existing_items = set([x[0] for x in UnicodeReader(f)])
    except IOError:
        existing_items = set()

    data = requests.get(URL).text
    content = [x.text for x in BeautifulSoup.BeautifulSoup(data).findAll('h4')]
    stars = [x.text for x in BeautifulSoup.BeautifulSoup(data).findAll('span', {'class': 'stars-sort'})]
    all_items = dict(zip(content, stars))
    new_items = OrderedSet(content) - existing_items

    for item, cost in all_items.iteritems():
        row = u'%s- %s (%s\u2606)' % (u'NEW ' if item in new_items else u'', item, cost)
        if verbose: print row

    try:
        first_label = new_items[0]
        first_cost = all_items[first_label]
        msg = u'%s new on %s eg %s (%s\u2606)' % (len(new_items), URL, first_label, first_cost)
        if verbose: print msg.encode('utf-8')

        auth = tweepy.OAuthHandler(CREDENTIALS['consumer_key'], CREDENTIALS['consumer_secret'])
        auth.set_access_token(CREDENTIALS['access_key'], CREDENTIALS['access_secret'])
        api = tweepy.API(auth)

        for r in recipients:
            api.send_direct_message(user=r, text=msg)

        with open(SCRAPE_FILE, 'w') as f:
            UnicodeWriter(f).writerows([[x] for x in all_items.iterkeys()])
    except IndexError:
        if verbose: print u'No new content'



parser = argparse.ArgumentParser(description='Scrape the Club Nintendo site')
parser.add_argument('recipients', nargs='+', help='One or more @names to send to')
parser.add_argument('-v', dest='verbose', action='store_true', default=False,
                   help='verbose mode')
args = parser.parse_args()
scrape(args.recipients, args.verbose)
