from os import environ
from datetime import datetime, timedelta

def mountain_time(zulu):
	MST_TIME_OFFSET = -5
	if environ['DAYLIGHT_SAVINGS']:
		offset = MST_TIME_OFFSET -1
	else:
		offset = MST_TIME_OFFSET	

	return zulu + timedelta(hours = offset)

if __name__ == "__main__":
    zulu = datetime.now()
    mtn = mountain_time(zulu)
    print("Local time: "+ str(mtn))
