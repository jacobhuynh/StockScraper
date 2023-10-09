import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

#ENTER STOCK TICKERS HERE
stockList = ["AAPL", "GOOG", "GOOGL", "AMZN", "META", "MSFT", "NVDA"]

stockDataFile = Workbook()
fileReader = stockDataFile.active
fileReader.title = "Data"

def getStockDataDict(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}"
    req = requests.get(url)

    webpage = BeautifulSoup(req.text, "html.parser")

    percentchange = webpage.find("fin-streamer", {"data-pricehint": "2", "data-field": "regularMarketChangePercent"}).text
    
    # alternative way:
    # price = webpage.find("span", {"class": "D(ib) Mend(20px)"}).find_all("span")[0].text -> goes to the class and finds all span tags and indexes through them
    
    stock = {
        "price": webpage.find("fin-streamer", {"data-pricehint": "2", "data-field": "regularMarketPrice"}).text,
        "change": webpage.find("fin-streamer", {"data-pricehint": "2", "data-field": "regularMarketChange"}).text,
        "percentchange": percentchange[1:len(percentchange)-1] 
    }
    return stock

def getStockDataArray(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}"
    req = requests.get(url)

    webpage = BeautifulSoup(req.text, "html.parser")

    percentchange = webpage.find("fin-streamer", {"data-pricehint": "2", "data-field": "regularMarketChangePercent"}).text
    estReturn = webpage.find("div", {"class": "Mb(8px)"}).text
    stock = [
        symbol,
        webpage.find("fin-streamer", {"data-pricehint": "2", "data-field": "regularMarketPrice"}).text,
        webpage.find("fin-streamer", {"data-pricehint": "2", "data-field": "regularMarketChange"}).text,
        percentchange[1:len(percentchange)-1],
        estReturn[0:estReturn.find(" ")]
    ]
    return stock

fileReader.append(["Symbol", "Price", "Change", "Percent Change", "Yahoo Estimated Return"])
for stock in stockList:
        fileReader.append(getStockDataArray(stock))
        print("Scrapping: " + stock),
        
print("Done")
stockDataFile.save("stockDataFile.xlsx")
    