from bs4 import BeautifulSoup
import requests
from datetime import time, timedelta, datetime
import re

global recordedBy
recordedBy = "test"

class AutoUploader:
    def __init__(self) -> None:
        self.wrs = None
        self.wr = None
        self.previousWr = None


    def getVideoFileURI(self):
        return input("URI to recorded world record (e.g. C:\\user\\video.mp4)")
    

    def getWrURL(self):
        return input("World record URL to parse: ")


    def scrapeWr(self):
        while True:
            try:
                url = requests.get(self.getWrURL())
                break
            except KeyboardInterrupt:
                exit("\nKeyboard interrupt")
            except:
                print("Not a valid URL. Couldn't fetch world record table.")


        url.encoding = url.apparent_encoding
        soup = BeautifulSoup(url.text, features='lxml')
        
        map = soup.find("div", attrs={'id': 'main'}).find('h2').text
        cc = soup.find("div", attrs={'id': 'main'}).find('b').text[-5:]
        table = soup.find("h2", text="History").findNext('table', attrs={'class': 'wr'})
        rows = table.find_all('tr')

        records = []
        for row in rows:
            record = row.find_all('td')
            record = [r.text for r in record]
            if len(record) == 14:
                userProfile = row.find("a", href=re.compile("profile.php"))['href']
                record.append(map)
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
        title = f"{wr.map} [{wr.cc}] - {wr.time} - {wr.player} (Mario Kart 8 Deluxe World Record)"
        print(f"Generated video title:\n  {title}")
        return title


    def generateVideoDescription(self):
        current, prev = self.wr, self.previousWr
        difference = self.getTimeDifference(current.time, prev.time)
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

    def getTimeDifference(self, t1, t2):
        wrTime = self.convertTimeString(t1)
        wrTime = datetime(2000, 1, 1,
            minute=wrTime["minutes"],
            second=wrTime["seconds"],
            microsecond=wrTime["milliseconds"]*1000
        )

        previousWrTime = self.convertTimeString(t2)
        previousWrTime = datetime(2000, 1, 1,
            minute=previousWrTime["minutes"],
            second=previousWrTime["seconds"],
            microsecond=previousWrTime["milliseconds"]*1000
        )

        current, prev = wrTime.timestamp(), previousWrTime.timestamp()
        difference = round(prev - current, 3)

        return difference


    def convertTimeString(self, time):
        time = time.replace(":", " ").replace(".", " ").split()
        try:
            converted = {
                "minutes": int(time[0]),
                "seconds": int(time[1]),
                "milliseconds": int(time[2])
            }
        except IndexError:
            print("Index error occured when formatting time from scraped data")

        return converted  

    
    def getApiCredentials(self):
        pass
    
    def uploadToYoutube(self):
        pass


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
        self.map = d[14]
        self.cc = d[15]
        self.profile = d[16]


while True:
    auto = AutoUploader()
    auto.scrapeWr()
    auto.generateVideoTitle()
    print(auto.generateVideoDescription())
