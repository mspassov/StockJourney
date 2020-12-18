CREATE TABLE person (
	username VARCHAR PRIMARY KEY,
	fname VARCHAR NOT NULL,
	lname VARCHAR NOT NULL,
	password VARCHAR NOT NULL, 
	cashInvested INTEGER,
	newUser INTEGER NOT NULL
	cashAvailable INTEGER NOT NULL
);
#newUser is used to check if a user has logged in for the first time, if so, they will be given the questionnaire

CREATE TABLE stock (
	username VARCHAR NOT NULL,
	ticker VARCHAR NOT NULL,
	numShares INTEGER NOT NULL,
	purchasePrice DECIMAL DEFAULT 0,
	PRIMARY KEY(username, ticker),
	FOREIGN KEY(username) REFERENCES person(username)
);

