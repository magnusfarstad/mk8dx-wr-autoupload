import requests
import re
import httplib2
import os
import random
import sys
import time

from bs4 import BeautifulSoup
from datetime import time, timedelta, datetime
from gooey import Gooey, GooeyParser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

httplib2.RETRIES = 1

global recordedBy
recordedBy = "test"

class WorldRecord:
    def __init__(self, scrapedData: list) -> None:
        d = scrapedData
        self.date = d[0]
        self.time = d[1].replace("'", ":").replace("\"", ".").strip()
        self.player = d[2]
        self.lasted = d[4]
        self.splits = f"{d[5]} - {d[6]} - {d[7]}"
        self.coins = d[8]
        self.shrooms = d[9]
        self.character = d[10]
        self.kart = d[11]
        self.wheels = d[12]
        self.glider = d[13]
        self.track = d[14]
        self.cc = d[15]
        self.profile = d[16]


class AutoUploader:
    def __init__(self) -> None:
        self.MAX_RETRIES = 10
        self.RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError)
        self.RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
        self.CLIENT_SECRETS_FILE = "client_secrets.json"
        self.YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
        self.YOUTUBE_API_SERVICE_NAME = "youtube"
        self.YOUTUBE_API_VERSION = "v3"
        self.VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

        self.wrs = None
        self.wr = None
        self.previousWr = None


    def getVideoFileURI(self):
        return input("URI to recorded world record (e.g. C:\\user\\video.mp4)")
    

    def getWrURL(self, track_url):
        while True:
            try:
                input("World record URL to parse: ")
                url = requests.get(track_url)
                url.encoding = url.apparent_encoding # UTF-8
                break
            except KeyboardInterrupt:
                exit("\nKeyboard interrupt")
            except:
                print("Not a valid URL. Couldn't fetch world record table.")

        return url


    def scrapeWr(self):
        data = self.getWrUrl()
        soup = BeautifulSoup(data.text, features='lxml')
        
        track = soup.find("div", attrs={'id': 'main'}).find('h2').text
        cc = soup.find("div", attrs={'id': 'main'}).find('b').text[-5:]
        table = soup.find("h2", text="History").findNext('table', attrs={'class': 'wr'})
        rows = table.find_all('tr')

        records = []
        for row in rows:
            record = row.find_all('td')
            record = [r.text for r in record]
            if len(record) == 14:
                userProfile = row.find("a", href=re.compile("profile.php"))['href']
                record.append(track)
                record.append(cc)
                record.append(userProfile)
                record = WorldRecord(record)
                records.append(record)

        self.wr = records[-1]
        self.previousWr = records[-2]
        print("Successfully scraped world records:\n"
              f"  1st: {self.wr.time} ({self.wr.player})\n"
              f"  2nd: {self.previousWr.time} ({self.previousWr.player})")

    
    def generateVideoTitle(self):
        wr = self.wr
        title = f"{wr.track} [{wr.cc}] - {wr.time} - {wr.player} (Mario Kart 8 Deluxe World Record)"
        print(f"Generated video title:\n  {title}")
        return title


    def generateVideoDescription(self):
        current, prev = self.wr, self.previousWr
        difference = self.formatDifference(self.getTimeDifference(current.time, prev.time))
        plural = "s" if current.lasted != "<1" else ""

        desc = (f"Date: {current.date}\n"
                f"{difference} improvement over previous WR: {prev.time} by {prev.player} on {prev.date} (lasted {current.lasted} day{plural})\n\n"
                f"Combo: {current.character} / {current.kart} / {current.wheels} / {current.glider}\n"
                f"Splits: {current.splits}\n"
                f"Mushrooms: {current.shrooms}\n"
                f"Coins: {current.coins}\n"
                f"User profile: https://www.mkwrs.com/mk8dx/{current.profile}\n\n"
                "See all the current and past WRs for MK8DX at: https://mkwrs.com/mk8dx\n"
                "See various top 10 leaderboards for MK8DX at: http://mkleaderboards.com/\n"
                "Discuss Time Trials in the MKLeaderboards Discord server!: /discord\n\n"
                "Enter the MK8DX time trial competition at: http://www.mariokartplayers.com/mk8\n"
                "Join the MK8DX online competitive scene at: http://www.mariokartcentral.com/\n\n"
                "If you want to watch WR videos for the Wii U version of MK8, refer to: /mk8records\n\n"
                f"Recorded by: {recordedBy}"
        )
        print("Generated video description...")
        return desc


    def getTimeDifference(t1: str, t2:str) -> timedelta:
        TIME_FORMAT = '%M:%S.%f'
        return (datetime.strptime(t1, TIME_FORMAT)
                - datetime.strptime(t2, TIME_FORMAT))
    

    def formatTimeDifference(difference: timedelta) -> str:
        sign = '-' if difference.days < 0 else ''
        if difference.days < 0:
            difference = - difference
        return f'{sign}{difference.seconds}.{difference.microseconds//1000:03}'


    def getAuthenticatedService(self, args):
        flow = flow_from_clientsecrets(self.CLIENT_SECRETS_FILE,
                                    scope=self.YOUTUBE_UPLOAD_SCOPE,
                                    message=self.MISSING_CLIENT_SECRETS_MESSAGE)

        storage = Storage("%s-oauth2.json" % sys.argv[0])
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, args)

        return build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION,
                    http=credentials.authorize(httplib2.Http()))
    
    
    def resumableUpload(self, insert_request):
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                print("Uploading file...")
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        print("Video id '%s' was successfully uploaded." %
                            response['id'])
                    else:
                        exit("The upload failed with an unexpected response: %s" % response)
            except HttpError as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                        e.content)
                else:
                    raise
            except self.RETRIABLE_EXCEPTIONS as e:
                error = "A retriable error occurred: %s" % e

            if error is not None:
                print(error)
                retry += 1
                if retry > self.MAX_RETRIES:
                    exit("No longer attempting to retry.")

                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                print("Sleeping %f seconds and then retrying..." % sleep_seconds)
                time.sleep(sleep_seconds)


    def initializeUpload(self, youtube, options, extra):
        tags = None
        if options.keywords:
            tags = options.keywords.split(",")

        body = dict(
            snippet=dict(
                title=options.title,
                description=options.description,
                tags=tags,
                categoryId=options.category
            ),
            status=dict(
                privacyStatus=options.privacyStatus
            )
        )

        # Call the API's videos.insert method to create and upload the video.
        insertRequest = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
        )

        self.resumableUpload(insertRequest)


    @Gooey
    def getArgs(self):
        argparser = GooeyParser()
        argparser.add_argument("--file", required=True, help="Video file to upload")
        argparser.add_argument("--url", required=True, help="Track URL to scrapte (mkwrs.com)", gooey_options={
                "placeholder": "mkwrs.com/(...)?track=Mario+Kart+Stadium&m=200"
            })
        #argparser.add_argument("--title", help="Video title", default="Test Title")
        #argparser.add_argument("--description", help="Video description", default="Test Description")
        argparser.add_argument("--category", default="22", help="Numeric video category. See https://developers.google.com/youtube/v3/docs/videoCategories/list")
        argparser.add_argument("--keywords", help="Video keywords, comma separated", default="")
        argparser.add_argument("--privacyStatus", choices=self.VALID_PRIVACY_STATUSES, default=self.VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
        args = argparser.parse_args()
        ## Du kan legge til title og description i initializeupload 

        if not os.path.exists(args.file):
            exit("Please specify a valid file using the --file= parameter.")

        youtube = getAuthenticatedService(args)
        try:
            initializeUpload(youtube, args, )
        except HttpError as e:
            print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


while True:
    auto = AutoUploader()
    args = auto.getArgs()
    auto.scrapeWr(args.url)
    auto.generateVideoTitle(args.url)
    print(auto.generateVideoDescription())
    



#!/usr/bin/python










# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.cloud.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")
