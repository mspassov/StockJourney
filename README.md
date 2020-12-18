# StockJourney - A Visual Portfolio Tracker
#### Try the website here: http://stock-journey.herokuapp.com/

StockJourney is a portfolio tracker, which uses the Yahoo Finance API to give users real-time stock quotes and portfolio tracking tools. 
The list of features that StockJourney supports:
<ul>
  <li>Creating an account, so that your portfolio is saved</li>
  <li>Searching and adding any ticker on any North American stock exchange, using real-time data</li>
  <li>Gathering detailed financial information about any public company</li>
  <li>Visualizing your portfolio using pie charts, bar graphs, and tables</li>
  <li>Seeing top performers, worst performers, and comparing your returns to any index as a benchmark</li>
  <li>Real-time currency conversion widget, directly built into the dashboard</li>
  <li>Real-time financial news</li>
  <li>Retirement planning tools, as well as "what if" analysis</li>
  <li>The wesbite supports a guided approach to investing, with stock recommendations based on your risk tolerance</li>
</ul>

##### The Technical Stuff
The website was created using a Python (flask) backend with an HTML/CSS/JS/Bootstrap front end. A PostgreSQL database was created, hosted on Heroku. 
The yahoo finance api was used to gather stock infromation. News API was used for news stories, and Fixer.io API was used for currency quotes.
