//////////////////////////////////////////
// Javascript for our sms web application
// 
// CB 7/2023

// Process sse based response to twillio message status pending


//////////////////////////////////////////
// work with css to style tabbed layout
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
  function mysqlDatetoJs(mysqlTimeStamp){
      var t = mysqlTimeStamp.split(/[- :]/);
          return new Date(t[0], t[1]-1, t[2], t[3], t[4], t[5]);
  }

/////////////////////////////////////////////
// style the send message popup

function chatPopup( client ) {
  document.getElementById("chatForm_"+String(client)).style.display = "block";
}

function closePopup( client ) {
  document.getElementById("chatForm_"+String(client)).style.display = "none";
}

////////////////////////////////////////////
// display sse driven messages dynamically
// smsMessage is json of Class Message from .models
// need to add in name attributes
function AddChatElement(smsMessage){ 
    // does a tab for this client exist? if not create it
    let linkId, tabLink, buttonText, buttonContent

    linkId = "button_"+String(smsMessage.Client)
    const tabParent = document.getElementById("tab_parent");
    if (document.getElementById( linkId )){
      tabLink = document.getElementById( linkId ); 
    } else {
      tabLink = document.createElement("button"); // need button attributes
      tabLink.setAttribute("id",linkId);
      tabLink.setAttribute("class", "w3-button w3-border w3-block w3-right-align tablink");
      tabLink.setAttribute("onclick", "openTab(event,'sms_"+String(smsMessage.Client)+"')");
      buttonText = "Client: "+String(smsMessage.Client);  //// temp for now till we can get the name
      buttonContent = document.createTextNode(buttonText);
      tabLink.appendChild(buttonContent);
      tabParent.appendChild( tabLink );
    }
    

    // find the parent <div id="chat_parent"> This contains the messages as child <div>'s
    const chatParent = document.getElementById("chat_parent"); 

    let contentId, chatContent
    // as above we may need to create a new tabcontent <div> or locate the one that exists for client
    contentId = "sms_"+String(smsMessage.Client)
    if (document.getElementById( contentId )) {
      chatContent = document.getElementById( contentId ); 
    } else {
      chatContent = document.createElement("div");
      chatContent.setAttribute("id", contentId);
      chatContent.setAttribute("class", "w3-container tabcontent");
      chatContent.setAttribute("style", "display: none;");
      chatParent.appendChild( chatContent );
    }
    
    // build our child <div>
    const chatChild = document.createElement("div"); 
    chatContent.appendChild(chatChild);
    
    // add id and class
    let divClass, spanClass, divId

    if (smsMessage.Outgoing) {
      divClass = "chat-container chat-darker chat-msg-right"
      spanClass= "chat-time-right"
    } else {
      divClass = "chat-container chat-msg-left"
      spanClass="chat-time-left"
    }
    
    divId = "msg_" + String(smsMessage.id)
    chatChild.setAttribute("id",divId);  
    chatChild.setAttribute("class",divClass); 
    
    // the <p> element containing the text itself
    const newPar = document.createElement("p"); 
    chatChild.appendChild(newPar);
    const newContent = document.createTextNode(smsMessage.Body);
    newPar.appendChild(newContent);
    
    // the <span> element with the time and date
    const newSpan = document.createElement("span"); 
    chatChild.appendChild(newSpan);
    
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