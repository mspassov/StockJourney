import yfinance as yf
from datetime import datetime
import math
from googlesearch import search


def name_convert(self):

    searchval = 'yahoo finance '+ self
    link = []
    #limits to the first link
    for url in search(searchval, lang='es'):
        link.append(url)
        break

    link = str(link[0])
    link=link.split("/")
    if link[-1]=='':
        ticker=link[-2]
    else:
        x=link[-1].split('=')
        ticker=x[-1]

    return(ticker)



tick = name_convert('goog')


#tick = yf.Ticker('xuu.to')
#dictT = tick.info 

print(tick)

