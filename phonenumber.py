# make a Twilio valid phone number out of user input
from string import digits

def cleanphone(mystring):
    # remove non-digits
    mystring = ''.join(c for c in mystring if c in digits)
    
    default_area_code = "575"
    l = len(mystring)
    if l == 7:
        mystring = "+1"+default_area_code+ mystring
    elif l == 10:
        mystring = '+1'+mystring
    elif l == 11 and mystring[0] == "1":
        mystring = '+'+mystring
    else:
        mystring = ''

    return mystring

if __name__ == "__main__":
    phone = input("Phone Number ")
    phone = cleanphone(phone)
    print(phone)
