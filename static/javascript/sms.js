function openTab(evt, tabId) {
  var i, tabcontent, tablinks;

  // Get all elements with class="tabcontent" and hide them
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Get all elements with class="tablinks" and remove the class "active"
  tablinks = document.getElementsByClassName("tablink");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(tabId).style.display = "block";
  evt.currentTarget.className += " active";
}

// javascript to display sse driven messages dynamically
  function mysqlDatetoJs(mysqlTimeStamp){
      var t = mysqlTimeStamp.split(/[- :]/);
          return new Date(t[0], t[1]-1, t[2], t[3], t[4], t[5]);
  }
  function AddChatElement(smsMessage) // message is json of Class Message from .models
  {    

    // find the parent <div id="chat_parent"> This contains the messages as child <div>'s
    const parentDiv = document.getElementById("chat_parent"); 
    
    // build our child <div>
    const newDiv = document.createElement("div"); 
    parentDiv.appendChild(newDiv);
    
    // add id and class
    let divClass, spanClass, divId

    if (smsMessage.Outgoing) {
      divClass = "container darker"
      spanClass= "time-right"
    } else {
      divClass = "container"
      spanClass="time-left"
    }
    
    divId = "msg_" + String(smsMessage.id)
    newDiv.setAttribute("id",divId);  
    newDiv.setAttribute("class",divClass); 
    
    // the <p> element containing the text itself
    const newPar = document.createElement("p"); 
    newDiv.appendChild(newPar);
    const newContent = document.createTextNode(smsMessage.Body);
    newPar.appendChild(newContent);
    
    // the <span> element with the time and date
    const newSpan = document.createElement("span"); 
    newDiv.appendChild(newSpan);
    
    newSpan.setAttribute("class",spanClass);  // depends on incoming v. outgoing
    
    let Today = new Date();
    let tDate = Today.getDate();
    let tMonth = Today.getMonth();
    let Yesterday = new Date().setDate(Today.getDate() - 1);
    let yDate = new Date(Yesterday).getMonth();
    let yMonth = new Date(Yesterday).getMonth();
    let messageDateTime = mysqlDatetoJs(smsMessage.SentAt)
    let mDate = messageDateTime.getDate();
    let mMonth = messageDateTime.getMonth();
    
    if (tDate == mDate && tMonth == mMonth) {
      timeStr = messageDateTime.toLocaleTimeString(); // the time
    } else if (yDate == mDate && yMonth == mMonth) {
      timeStr = "Yesterday at "+ messageDateTime.toLocaleTimeString();
    } else {
      timeStr = messageDateTime.toDateString();// the date
    }
    
    const timeContent = document.createTextNode(timeStr);
    newSpan.appendChild(timeContent);

  }