from datetime import datetime
# convert suggested dob string to dob in standard format

def cleandob(dob):
	# dashes to slashes
	dob = dob.replace('-', '/')

	# assume < 100yo unless four digit year (over ride datetime which uses this century)
	this_year = datetime.today().year
	yob = int(dob.split('/')[2])

	if yob < 100 and yob + 2000 > this_year:
		yob += 1900
	else:
		yob += 2000
	 

	# check for valid date string
	# prioritize the more common varients. Accept the first one that matches.
	try:
		date_obj = datetime.strptime(dob, '%m/%d/%y')
		date_obj = date_obj.replace(year=yob)
	except ValueError:
		try:
			date_obj = datetime.strptime(dob, '%m/%d/%Y')
		except ValueError: # maybe they are from Europe
			try:
				date_obj = datetime.strptime(dob, '%d/%m/%y')
				date_obj = date_obj.replace(year=yob)
			except ValueError:
				try:
					date_obj = datetime.strptime(dob, '%d/%m/%Y')
				except ValueError: # maybe from the army
					try:
						date_obj = datetime.strptime(dob, '%Y/%m/%d')
					except:  # just give up
						date_obj = None

	if date_obj: # replace with standard string for DB
		dob = date_obj.strftime("%m/%d/%Y")
	else:
		dob = None

	return dob

if __name__ == "__main__":
    dob = input("Birthdate ")
    dob = cleandob(dob)
    print(dob)
