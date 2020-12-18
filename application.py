import os
import requests
import flask
import yfinance as yf
import math
import decimal
import json

from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from math import ceil
from datetime import datetime
from flask_table import Table, Col
from googlesearch import search

app = Flask(__name__)
app.secret_key = "averysecurekey"

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Method to calculate different performance metrics.
def performances(stock_info, values, numShares, prices):
	# Calculating individual performances
	yday_close = [stock['regularMarketPreviousClose'] for stock in stock_info]
	returns = [round(100*(prices[i]/yday_close[i] - 1),2) for i in range(len(values))]
	tickers = [stock['symbol'] for stock in stock_info]

	# Creating a dictionary matching returns with tickers
	ticker_returns = {}
	for i in range(len(tickers)):
		ticker_returns[returns[i]] = i

	# Getting top and bottom performers
	num_top_performers = min(ceil(len(tickers)/2), 4)
	num_bot_performers = min(len(tickers)-num_top_performers, 4)
	top_performers = sorted(ticker_returns, reverse=True)[0:num_top_performers]
	top_performers = {returns: ticker_returns[returns] for returns in top_performers}
	bot_performers = sorted(ticker_returns)[0:num_bot_performers]
	bot_performers = {returns: ticker_returns[returns] for returns in bot_performers}

	# Getting daily total profit/loss as well as market profit/loss
	yday_values = [round(yday_close[i] * numShares[i],2) for i in range(len(numShares))]
	overall_performance = round(100 *(sum(values) / sum(yday_values) - 1),2) if sum(yday_values) != 0 else 0
	sp500 = yf.Ticker('^GSPC').info
	mkt_performance = round(100*(sp500['regularMarketPrice']/sp500['regularMarketPreviousClose'] - 1),2)

	return(returns, overall_performance, mkt_performance, top_performers, bot_performers)

# Method to get data to populate dashboard
def getDashboard(username):
	# Getting user's holdings and cash available.
	holdings = [row for row in db.execute("SELECT ticker, numShares FROM stock WHERE username = :username", {"username": username})]
	db.commit()
	cashAvailable = [row for row in db.execute("SELECT cashAvailable FROM person WHERE username = :username", {"username": username})][0][0]
	db.commit()
	cashAvailable = round(cashAvailable,2)

	# Getting the information regarding their current porfolio.
	tickers = [ticker for (ticker, numShares) in holdings]
	stock_info = [yf.Ticker(ticker).info for ticker in tickers]
	numShares = [numShare for (ticker, numShare) in holdings]
	prices = [stock['regularMarketPrice'] for stock in stock_info]
	values = [round(prices[i] * numShares[i],2) for i in range(len(numShares))]
	chart_colors = ['#FFFFB3', '#8DD3C7','#BEBADA', '#80B1D3','#FDB462','#FCCDE5','#D9D9D9','#BC80BD','#FFED6F'] 
	chart_color_final = chart_colors[0:len(tickers)]
	# Computing portfolio performance metrics.
	(returns, overall_performance, mkt_performance, top_performers, bot_performers) = performances(stock_info, values, numShares, prices)
	
	top_returns = list(top_performers.keys())
	bot_returns = list(bot_performers.keys())

	top_tickers = [tickers[index] for index in list(top_performers.values())]
	bot_tickers = [tickers[index] for index in list(bot_performers.values())]

	top_names = [stock_info[index]['longName'].replace('&amp;', '&') for index in list(top_performers.values())]
	bot_names = [stock_info[index]['longName'].replace('&amp;', '&') for index in list(bot_performers.values())]

	top_current = [prices[index] for index in list(top_performers.values())]
	bot_current = [prices[index] for index in list(bot_performers.values())]

	top_close = [stock_info[index]['regularMarketPreviousClose'] for index in list(top_performers.values())]
	bot_close = [stock_info[index]['regularMarketPreviousClose'] for index in list(bot_performers.values())]

	top_num_shares = [numShares[index] for index in list(top_performers.values())]
	bot_num_shares = [numShares[index] for index in list(bot_performers.values())]


	return render_template("dashboard.html", tickers = tickers, numShares = numShares, 
		values=values, cashAvailable="{0:,.2f}".format(cashAvailable), totalValue = "{0:,.2f}".format(sum(values)),
		overall_performance = overall_performance, mkt_performance = mkt_performance, top_names = top_names,top_tickers=top_tickers,
		bot_tickers=bot_tickers, bot_names = bot_names, top_returns = top_returns, bot_returns=bot_returns, top_current = top_current,
		bot_current = bot_current, top_close=top_close, bot_close=bot_close, top_num_shares=top_num_shares, bot_num_shares=bot_num_shares, chart_color_final=chart_color_final)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
	return render_template("login.html")

@app.route("/register")
def register():
	return render_template("register.html")


@app.route("/home", methods=["POST", "GET"])
def home():
	username=session['username']
	return getDashboard(username)

@app.route("/registerComplete", methods=["POST"])
def registerComplete():
	firstName = request.form.get('fname')
	lastName = request.form.get('lname')
	username = request.form.get('username')
	password = request.form.get('password')
	confirmedP = request.form.get('cpassword')

	if firstName == "" or lastName == "" or username == "" or password == "" or confirmedP ==  "":
		return render_template("register.html", message="Please fill all the fields")

	if password != confirmedP:
		return render_template("register.html", message="Passwords do not match")

	row = db.execute("SELECT * FROM person WHERE username = :username", {"username": username}).rowcount;
	db.commit()

	if row == 1:
		return render_template("register.html", message="Username is already taken")
	else:
		db.execute("INSERT INTO person(username, fname, lname, password, cashInvested, newUser) VALUES(:username, :firstName, :lastName, :password, 0, 1)", {"username": username, "firstName": firstName, "lastName": lastName, "password": password})
		db.commit()

	return render_template("index.html", check="registered")

@app.route('/loginComplete', methods=['POST', 'GET'])
def loginComplete():
	username = request.form.get('username')
	password = request.form.get('password')

	row = db.execute("SELECT * FROM person WHERE username = :username AND password = :password", {"username": username, "password": password}).rowcount
	db.commit()

	query = db.execute("SELECT * FROM person WHERE username = :username AND password = :password", {"username": username, "password": password}).fetchall()
	db.commit()

	if row == 0:
		return render_template("login.html", message="Wrong credentials")

	session['username'] = query[0][0]

	if query[0][5] == 1:
		#this means user has never logged in before, present the questionnaire

		return render_template("getstarted.html")

	return getDashboard(username)

@app.route('/startPage', methods=['POST'])
def startPage():
	return render_template('getstarted.html')

@app.route('/manual', methods=["POST", "GET"])
def manual():
	session['userType'] = "expert"
	return render_template("manualProfile.html")

@app.route("/profilerecommend", methods=["POST", "GET"])
def profilerecommend():

	if flask.request.method == "POST":
		risk1 = int (request.form.get("question1"))
		risk2 = int (request.form.get("question2"))
		risk3 = int (request.form.get("question3"))
		initialAmount = request.form.get('amountInvested')

		if initialAmount != "":
			session['currentAmt'] = int(initialAmount)
		else:
			session['currentAmt'] = 0

		updateQ1 = db.execute("UPDATE person SET cashInvested= :amt WHERE username= :username", {'amt': session['currentAmt'], 'username':session['username']})
		db.commit()

		updateQ2 = db.execute("UPDATE person SET cashAvailable= :amt WHERE username= :username", {'amt': session['currentAmt'], 'username':session['username']})
		db.commit()

		#this makes sure that users don't keep going back and forth on the pages
		session['furtherRisk'] = 0

		session['furtherRisk'] = risk1 + risk2 + risk3

		totalRisk = session['furtherRisk'] + session['initialRisk']
	else:
		totalRisk = 6

	if totalRisk <= 4:
		return render_template("profilerecommend.html", message="low")
	elif totalRisk <= 8:
		return render_template("profilerecommend.html", message="medium")
	else:
		return render_template("profilerecommend.html", message="high")

@app.route("/whyinvest", methods=['POST', "GET"])
def whyinvest():
	session['userType'] = "novice"
	return render_template("whyinvest.html")

@app.route("/questions", methods=['POST', 'GET'])
def questions():

	if flask.request.method == "POST":
		risk = int(request.form.get("optionSelect"))
		session['initialRisk'] = risk


	return render_template("questions.html")


@app.route("/recommendation", methods=["POST"])
def recommendation():

	totalRisk = request.form.get("profileSelect")

	if totalRisk == "low":
		zag = 70
		vfv = 10
		xuu = 10
		xef = 10
		return render_template("recommendations.html", zag=zag, vfv=vfv, xuu=xuu, xef=xef)
	elif totalRisk == "medium":
		zag = 40
		vfv = 20
		xuu = 20
		xef = 20
		return render_template("recommendations.html", zag=zag, vfv=vfv, xuu=xuu, xef=xef)
	else:
		zag = 10
		vfv = 30
		xuu = 30
		xef = 30
		return render_template("recommendations.html", zag=zag, vfv=vfv, xuu=xuu, xef=xef)

@app.route("/dashboard", methods=["POST", "GET"])
def dashboard():
	#if they make it this far, then you update the db, so that they never see the questionnaire again
	username = session['username']
	updateQ = db.execute("UPDATE person SET newUser = 0 WHERE username = :username", {"username": username})
	db.commit()

	if session['userType'] == "expert":
		amount = request.form.get('amountInvested')
		if amount == "":
			amount = 0
		amount = int(amount)
		updateQ1 = db.execute("UPDATE person SET cashInvested= :amt WHERE username= :username", {'amt': amount, 'username':session['username']})
		db.commit()

		updateQ2 = db.execute("UPDATE person SET cashAvailable= :amt WHERE username= :username", {'amt': amount, 'username':session['username']})
		db.commit()

	#this means that you went through the beginner flow, and may have selected starting stocks
	if session['userType'] == "novice":
		zagAlloc = int(request.form.get('zag')) / 100
		vfvAlloc = int(request.form.get('vfv')) / 100
		xuuAlloc = int(request.form.get('xuu')) / 100
		xefAlloc = int(request.form.get('xef')) / 100


		zagP = yf.Ticker('ZAG.TO').info['regularMarketPrice']
		vfvP = yf.Ticker('VFV.TO').info['regularMarketPrice']
		xuuP = yf.Ticker('XUU.TO').info['regularMarketPrice']
		xefP = yf.Ticker('XEF.TO').info['regularMarketPrice']

		cash = session["currentAmt"]

		zagShares = math.floor( (zagAlloc * cash) / zagP )
		vfvShares = math.floor( (vfvAlloc * cash) / vfvP )
		xuuShares = math.floor( (xuuAlloc * cash) / xuuP )
		xefShares = math.floor( (xefAlloc * cash) / xefP )

		totalCashSpent = zagShares * zagP + vfvShares * vfvP + xuuShares * xuuP + xefShares * xefP
		cashRemaining = cash - totalCashSpent

		#first update the db to reflect the cash spent
		query2 = db.execute("UPDATE person SET cashAvailable = :avail WHERE username = :username", {'avail': cashRemaining, 'username': username})
		db.commit()

		#Add the stocks, and number of shares to the database
		try:
			if zagAlloc > 0:
				query3 = db.execute("INSERT INTO stock(username, ticker, numShares, purchasePrice) VALUES(:username, :t, :n, :p)", {"username": username, "t": 'ZAG.TO', "n": zagShares, 'p':zagP})
				db.commit()
			if vfvAlloc > 0:
				query4 = db.execute("INSERT INTO stock(username, ticker, numShares, purchasePrice) VALUES(:username, :t, :n, :p)", {"username": username, "t": 'VFV.TO', "n": vfvShares, 'p':vfvP})
				db.commit()
			if xuuAlloc > 0:
				query5 = db.execute("INSERT INTO stock(username, ticker, numShares, purchasePrice) VALUES(:username, :t, :n, :p)", {"username": username, "t": 'XUU.TO', "n": xuuShares, 'p':xuuP})
				db.commit()
			if xefAlloc > 0:
				query6 = db.execute("INSERT INTO stock(username, ticker, numShares, purchasePrice) VALUES(:username, :t, :n, :p)", {"username": username, "t": 'XEF.TO', "n": xefShares, 'p':xefP})
				db.commit()
		except:
			print('already added')
	return getDashboard(username)

@app.route("/logout", methods=["POST"])
def logout():
	session.pop("user", None)

	return render_template('index.html');

#The currency calculator routing and GET from exchangerate API
@app.route("/currency", methods=["POST", "GET"])
def currency():
	amount = request.form.get('amount')
	base = request.form.get('base')
	to = request.form.get('to')

	# Placeholders
	if(base==None):
		base = "USD"
		to = "CAD"

	if(amount==None):
		amount = 1000
	elif(amount==""):
		amount = 0
	amount = int(amount)


	req_data = requests.get('https://api.exchangeratesapi.io/latest')
	response = json.loads(req_data.text)

	outputBase = 1
	outputTo = 1

	if(base == 'EUR') and (to == 'EUR'):
		outputBase = 1
		outputTo = 1

	elif(base == 'EUR') and (to != 'EUR'):
		outputBase = 1
		outputTo = response['rates'][to]
		base = 'EUR'

	elif(base!='EUR') and (to == 'EUR'):
		outputBase = response['rates'][base]
		outputTo = 1
		to = 'EUR'

	else:
		outputBase = response['rates'][base]
		outputTo = response['rates'][to]

	outputBaseAmount1 = round( ( (1 / outputBase) * outputTo) , 2)
	outputToAmount1 = round( ( (1 / outputTo) * outputBase) , 2)

	outputAmount = round( ( (amount / outputBase) * outputTo) , 2 )


	amount = "{:,}".format(amount)
	outputAmount = "{:,}".format(outputAmount)


	#Now for News Cards API
	news_data = requests.get('https://newsapi.org/v2/everything?q=currency+rate&apiKey=5d8559e90d254aaa8c4a7e9858724867')
	#For headline US business news:  http://newsapi.org/v2/top-headlines?country=us&category=business&apiKey=5d8559e90d254aaa8c4a7e9858724867
	news_response = json.loads(news_data.text)

	news1Title = news_response['articles'][1]['title']
	news1Img = news_response['articles'][1]['urlToImage']
	news1URL = news_response['articles'][1]['url']

	news2Title = news_response['articles'][2]['title']
	news2Img = news_response['articles'][2]['urlToImage']
	news2URL = news_response['articles'][2]['url']

	news3Title = news_response['articles'][3]['title']
	news3Img = news_response['articles'][3]['urlToImage']
	news3URL = news_response['articles'][3]['url']

	news4Title = news_response['articles'][4]['title']
	news4Img = news_response['articles'][4]['urlToImage']
	news4URL = news_response['articles'][4]['url']

	return render_template('currency.html', amount=amount, base=base, to=to, outputBase=outputBase, outputTo=outputTo, outputAmount=outputAmount,
		outputBaseAmount1=outputBaseAmount1, outputToAmount1=outputToAmount1, 
		news1Title=news1Title, news1Img=news1Img, news1URL=news1URL,
		news2Title=news2Title, news2Img=news2Img, news2URL=news2URL,
		news3Title=news3Title, news3Img=news3Img, news3URL=news3URL,
		news4Title=news4Title, news4Img=news4Img, news4URL=news4URL)


#The retirement calculator routing and GET from exchangerate API
@app.route("/retirement", methods=["POST", "GET"])
def retirement():
	currentage = request.form.get('currentage')
	retirementage = request.form.get('retirementage')
	monthlycontr = request.form.get('monthlycontr')
	risk = request.form.get('risk')
	existingsavings = request.form.get('existingsavings')

	savingsamount = []
	years = []
	monthly = []

	if(currentage==None):
		currentage = 0
	elif(currentage==""):
		currentage = 0
	currentage = int(currentage)

	if(retirementage==None):
		retirementage = 0
	elif(retirementage==""):
		retirementage = 0
	retirementage = int(retirementage)

	if(existingsavings==None):
		existingsavings = 0
	elif(existingsavings==""):
		existingsavings = 0
	existingsavings = int(existingsavings)

	if(monthlycontr==None):
		monthlycontr = 0
	elif(monthlycontr==""):
		monthlycontr = 0
	monthlycontr = int(monthlycontr)

	#annual return"{0:,.2f}".format(cashAvailable)
	if risk == 'Conservative':
		annualreturn = 1.05
	elif risk == 'Balanced':
		annualreturn = 1.10
	else:
		annualreturn = 1.15

	yearly_contribution = monthlycontr * 12
	years_until_retirement = retirementage - currentage
	savings = existingsavings

	initialplusmonthly = existingsavings

	for x in range(1, years_until_retirement+1):
		years.append(x)
		initialplusmonthly += yearly_contribution
		monthly.append(initialplusmonthly)

	for x in range(1, years_until_retirement+1):
		savings += yearly_contribution
		savings = savings * annualreturn
		savings = round(savings, 2)
		savingsamount.append(savings)

	#graph
	max = savings
	#savings = "{:.2f}".format(savings)
	savings = "{0:,.2f}".format(savings)

	#total savings
	line_labels=years
	line_values=savingsamount
	#maxval = savingsamount

	#initial plus monthly total
	line_values2=monthly
	#maxval2 = initialplusmonthly

	return render_template('retirement.html', monthly=monthly, values2=line_values2, max=max, currentage=currentage, retirementage=retirementage, monthlycontr=monthlycontr, risk=risk, labels=line_labels, values=line_values, savings=savings)

@app.route('/trade', methods=["GET"])
def trade():
	query = db.execute('SELECT cashAvailable FROM person WHERE username = :username', {'username': session['username']}).fetchall();
	db.commit()

	return render_template('trade.html', cash=query[0][0], flag="false", price=-50)

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

@app.route('/stockSearch', methods=	["POST"])
def stockSearch():

	query = db.execute('SELECT cashAvailable FROM person WHERE username = :username', {'username': session['username']}).fetchall();
	db.commit()

	tickerName = name_convert(request.form.get('ticker'))

	try:
		price = yf.Ticker(tickerName).info['regularMarketPrice']
		try:
			companyName = yf.Ticker(tickerName).info['shortName']
		except:
			companyName = ""
		try:
			vol = "{:,}".format(int(yf.Ticker(tickerName).info['averageVolume']))
		except:
			vol = ""
		try:
			beta = yf.Ticker(tickerName).info['beta']
		except:
			beta = ""
		try:
			mcap = "{:,}".format(int(yf.Ticker(tickerName).info['marketCap']))
		except:
			mcap = ""
		try:
			pe = yf.Ticker(tickerName).info['forwardPE']
		except:
			pe = ""
		try:
			floatDiv = float(yf.Ticker(tickerName).info['dividendYield']) * 100
		except:
			floatDiv = ""
		try:
			div = '{0: .2f}'.format(floatDiv)
		except:
			div = ""
		try:
			eps = yf.Ticker(tickerName).info['forwardEps']
		except:
			eps = ""
		try:
			so = "{:,}".format(int(yf.Ticker(tickerName).info['sharesOutstanding']))
		except:
			so = ""

		session['search'] = tickerName.upper()
		message=""
	except:
		price = -100
		companyName = ""
		vol = ""
		beta = ""
		mcap = ""
		pe = ""
		div =""
		eps =""
		so = ""
		message = "Ticker does not exist, pleae try again"
		return render_template('trade.html', price=price, flag='false', cash=query[0][0], message=message, vol=vol, beta=beta, mcap=mcap, pe=pe, div=div, eps=eps, so=so)

	#See if we own any of the shares
	query2 = db.execute('SELECT * from stock WHERE username = :user AND ticker = :ticker', {'user': session['username'], 'ticker': tickerName.upper()}).rowcount
	db.commit()

	if query2 == 0:
		numShares = 0
	else:
		query3 = db.execute('SELECT * from stock WHERE username = :user AND ticker = :ticker', {'user': session['username'], 'ticker': tickerName.upper()}).fetchall()
		db.commit()
		numShares = query3[0][2]

	#output the graph for the stock
	tick = yf.Ticker(tickerName.upper())
	hist = tick.history(period='10y', interval='3mo')
	myList = hist['Close'].values.tolist()
	fList = []

	for i in myList:
		if math.isnan(i) == False:
			fList.append(i)

	myDates = hist.index.tolist();
	strDate=[]

	for i in range(len(myDates)):
		strDate.append(myDates[i].strftime('%Y-%m-%d'))

	if fList[0] > fList[-1]:
		bgColor = '#ff7066'
		borderColor = '#d10000'
	else:
		bgColor = '#bfe283'
		borderColor = '#009900'

	strDate = strDate[0: len(fList)]

	return render_template('trade.html', ticker=tickerName.upper(), price=price, cash=query[0][0], name=companyName, quantity=numShares, message=message, flag='true', myList=fList, strDate=strDate, bgColor=bgColor, borderColor=borderColor, vol=vol, beta=beta, mcap=mcap, pe=pe, div=div, eps=eps, so=so)

@app.route('/addFunds', methods=["POST"])
def addFunds():
	money = int(request.form.get('funds'))
	signal = request.form.get('b1')

	query = db.execute('SELECT cashAvailable FROM person WHERE username = :user', {'user': session['username']}).fetchall()
	db.commit()

	currentMoney = query[0][0]

	if signal == 'add':
		newMoney = currentMoney + money
		query2 = db.execute('UPDATE person SET cashAvailable = :cash WHERE username = :user', {'cash': newMoney, 'user':session['username']})
		db.commit()
		return getDashboard(session['username'])
	else:
		newMoney = currentMoney - money
		query2 = db.execute('UPDATE person SET cashAvailable = :cash WHERE username = :user', {'cash': newMoney, 'user':session['username']})
		db.commit()
		return getDashboard(session['username'])

@app.route('/executeTrade', methods=["POST"])
def executeTrade():
	price = -50
	cashAvail = 0
	signal = request.form.get('shareBtn')
	quant = int(request.form.get('numShares'))

	if signal == "buy":
		stockPrice = int(yf.Ticker(session['search']).info['regularMarketPrice'])
		value = quant * stockPrice

		query = db.execute('SELECT cashAvailable FROM person WHERE username = :username', {'username': session['username']}).fetchall();
		db.commit()

		cashAvail = query[0][0]
		if value > cashAvail:
			price = -100
			message = "Insufficient funds to execute trade, lower the quantity or fund account"
			return render_template('trade.html', price=price, message=message, flag='false')


		else:
			#This means that we can update/insert stock into account
			query = db.execute('SELECT * FROM stock WHERE username = :username and ticker = :ticker', {'username':session['username'], 'ticker': session['search'].upper()}).rowcount
			db.commit()

			#we own this stock, so we can just update the table
			if query == 1:

				queryN = db.execute('SELECT numShares FROM stock WHERE username = :user AND ticker = :ticker', {'user': session['username'], 'ticker': session['search']}).fetchall();
				db.commit()

				currShares = queryN[0][0] + quant

				queryU = db.execute('UPDATE stock SET numShares = :num WHERE username = :user AND ticker = :ticker', {'num': currShares, 'user': session['username'], 'ticker': session['search']})
				db.commit()

				cashAvail = cashAvail - value
				queryU2 = db.execute('UPDATE person SET cashAvailable = :cash WHERE username = :user', {'cash': cashAvail, 'user': session['username']})
				db.commit()
			else:
			#we don't have this stock, so we insert it
				queryE = db.execute('INSERT INTO stock(username, ticker, numShares, purchasePrice) VALUES(:user, :ticker, :num, :price)', {'user': session['username'], 'ticker': session['search'], 'num': quant, 'price': stockPrice})
				db.commit()

				cashAvail = cashAvail - value
				queryU2 = db.execute('UPDATE person SET cashAvailable = :cash WHERE username = :user', {'cash': cashAvail, 'user': session['username']})
				db.commit()

			price= -49
			message = "Successfully purchased shares"
			return render_template('trade.html', price=price, message=message, cash=cashAvail, flag='false')
	else:
		#this means we want to sell
		query5 = db.execute('SELECT numShares from stock where username= :user and ticker= :ticker', {'user': session['username'], 'ticker': session['search']}).fetchall()
		db.commit()

		query6 = db.execute('SELECT cashAvailable FROM person WHERE username = :username', {'username': session['username']}).fetchall();
		db.commit()

		cashAvail = query6[0][0]

		quantOwned = query5[0][0]

		if quantOwned < quant:
			price= -100
			message = "You are selling more shares than you own, please decrease the quantity"
			return render_template('trade.html', price=price, cash=cashAvail, flag='false', message=message)
		else:
			stockPrice = int(yf.Ticker(session['search']).info['regularMarketPrice'])
			cashAvail = cashAvail + stockPrice*quant

			queryU = db.execute('UPDATE person set cashAvailable= :cash WHERE username = :user', {'cash': cashAvail, 'user': session['username']})
			db.commit()

			newShares = quantOwned - quant
			queryU2 = db.execute('UPDATE stock set numShares = :num where username = :user and ticker = :ticker', {'num': newShares, 'user': session['username'], 'ticker': session['search']})
			db.commit()

			message = "Successfully sold your shares"
			price = -20

			#delete the ticker if you have sold all the shares
			if quantOwned == quant:
				query = db.execute('DELETE FROM stock WHERE username = :user and ticker= :ticker', {'user': session['username'], 'ticker': session['search']})
				db.commit()

			return render_template('trade.html', price=price, cash=cashAvail, flag='false', message=message)


@app.route('/portfolio', methods=["GET", "POST"])
def portfolio():
	class StockTable(Table):
		name = Col('Name')
		ticker = Col('Ticker')
		num_shares = Col('Shares Owned')
		purchase_price = Col('Purchase Price')
		current_price = Col('Current Price')
		daily_return = Col('Today\'s Return')
		overall_return = Col('Total Return')



	username = session['username']
	holdings = [row for row in db.execute("SELECT ticker, numShares, purchasePrice FROM stock WHERE username = :username", {"username": username})]
	tickers = [ticker for (ticker, numShares, purchasePrice) in holdings]
	numShares = [numShare for (ticker, numShare, purchasePrice) in holdings]
	stock_info = [yf.Ticker(ticker).info for ticker in tickers]
	names = [stock['longName'] for stock in stock_info]
	names = [name.replace('&amp;', '&') for name in names]
	purchase_price = [purchasePrice for (ticker,numShares,purchasePrice) in holdings]
	current_price = [round(decimal.Decimal(stock['regularMarketPrice']),2) for stock in stock_info]
	daily_return = [str(round(stock['regularMarketPrice']/stock['regularMarketPreviousClose'] * 100 - 100,2))+'%' for stock in stock_info]
	overall_return = [str(round(current_price[i] / purchase_price[i] * 100 - 100,2))+'%' for i in range(len(names))]

	items = [dict(name=names[i], ticker = tickers[i], num_shares = numShares[i], purchase_price=purchase_price[i], 
		current_price=current_price[i], daily_return=daily_return[i], overall_return=overall_return[i]) for i in range(len(tickers))]

	headers = ['Name', 'Ticker', 'Shares Owned', 'Purchase Price', 'Current Price', 'Today\'s Return', 'Total Return']

	table = StockTable(items, classes=['table', 'table-hover'])

	return render_template('portfolio.html', objects=items, headers = headers)

# app name
@app.errorhandler(404)
  
# inbuilt function which takes error as parameter
def not_found(e):
# defining function
  return render_template("404.html")



