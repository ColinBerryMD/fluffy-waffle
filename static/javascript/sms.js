//////////////////////////////////////////
// Javascript for our sms web application
// 
// CB 8/2023

// Process sse based response to twillio message and message status


//////////////////////////////////////////
// work with css to style tabbed layout
function openTab(evt, columnId, tabId) {
  var i, tabcontent, tablinks;

  let column = document.getElementById(columnId);

  // Get all elements with class="tabcontent" and hide them
  tabcontent = column.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Get all elements with class="tablinks" and remove the class "active"
  tablinks = column.getElementsByClassName("tablink");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(tabId).style.display = "block";
  evt.currentTarget.className += " active";
}
///////////////////////////////////////////////////
// return a humanized date/time stamp
// the complex part was moved to python
function messageTime(mysqlTimeStamp){
  let t =  mysqlTimeStamp.split(/[- : T]/);  // mysql time to js
  let msgDate = new Date(t[0], t[1]-1, t[2], t[3], t[4], t[5]);
  
  return msgDate.toLocaleTimeString([], { timeStyle: 'short' }); // the time won't need javascript if its not today
}                                                                // as it will be updated on server side

/////////////////////////////////////////////
// style the send message popup

function chatPopup( chatId ) {
  document.getElementById( chatId ).style.display = "block";
}

function closePopup( chatId ) {
  document.getElementById( chatId ).style.display = "none";
}

////////////////////////////////////////////
// display sse driven messages dynamically
// smsMessage is json of Class Message from .models
// need to add in name attributes
function AddChatElement(smsMessage){ 
    // does a tab for this client exist? if not create it
    let linkId, tabLink, buttonContent, fullName;

    linkId = "button_"+String(smsMessage.Client);
    const tabParent = document.getElementById("tab_parent");
    if (document.getElementById( linkId )){
      tabLink = document.getElementById( linkId ); 
    } else {
      tabLink = document.createElement("button"); // need button attributes
      tabLink.setAttribute("id",linkId);
      tabLink.setAttribute("class", "w3-button w3-border w3-block w3-right-align tablink");
      tabLink.setAttribute("onclick", "openTab(event,'sms_"+String(smsMessage.Client)+"')");
      fullName= smsMessage.sms_client.firstname+" "+smsMessage.sms_client.lastname;
      buttonContent = document.createTextNode(fullName);
      tabLink.appendChild(buttonContent);
      tabParent.appendChild( tabLink );
    }
    

    // find the parent <div id="chat_parent"> This contains the messages as child <div>'s
    const chatParent = document.getElementById("chat_parent"); 

    let contentId, chatContent
    // as above we may need to create a new tabcontent <div> or locate the one that exists for client
    contentId = "sms_"+String(smsMessage.Client);
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
    chatChild.setAttribute("id",smsMessage.sms_sid);
    chatContent.appendChild(chatChild);
    
    let divClass, spanClass;
    if (smsMessage.Outgoing) {
      divClass = "chat-container chat-outgoing";
      spanClass= "chat-time-right";
    } else {
      divClass = "chat-container chat-incoming";
      spanClass="chat-time-left";
    }
    
    chatChild.setAttribute("class",divClass); 
    
    // the <p> element containing the text itself
    const newPar = document.createElement("p"); 
    chatChild.appendChild(newPar);
    const newContent = document.createTextNode(smsMessage.Body);
    newPar.appendChild(newContent);
    
    // a span element to flag failed messages
    const failSpan = document.createElement("span"); 
    chatChild.appendChild(failSpan);
    failSpan.setAttribute("class",'chat-time-right chat-failed');
    failSpan.setAttribute("name",'flag-failure');
    failMsg = document.createTextNode("_message failed");
    failSpan.appendChild(failMsg);
    //failSpan.setAttribute("style","display: none;");

    // if the status is already known, ie failed
    chatChild.classList.add("status-"+smsMessage.sms_status);

    // the <span> element with the time and date
    const newSpan = document.createElement("span"); 
    chatChild.appendChild(newSpan);// the <span> element with the time and date
    newSpan.setAttribute("class",spanClass);  // depends on incoming v. outgoing

    const timeContent = document.createTextNode(messageTime(smsMessage.SentAt));
    newSpan.appendChild(timeContent);
}
////////////////////////////////////////////
// update an sms message status dynamically with sse
// we will change the appearance in css based on status
// 
function UpdateChatStatus(smsStatus){ 
  const chatChild = document.getElementById( smsStatus.sms_sid );
  chatChild.classList.remove("status-queued","status-sent","status-delivered","status-undelivered","status-failed");
  chatChild.classList.add("status-"+smsStatus.sms_status);
}
/////////////////////////////////////////////
// create a popup element to send a message
// given a sms_client() json
function AddSendPopup(client_json){ 
  //<div id="profile_form" style="display: none;">
  let profile_block = document.getElementById('profile_block');
  profile_block.setAttribute("style", "display: block;");

  // set competeing blocks to display:none
  let select_block = document.getElementById('select_block');
  select_block.setAttribute("style", "display: none;");
  let search_block = document.getElementById('search_block');
  search_block.setAttribute("style", "display: none;");

  // create an action attribute like action=url_for('message.send', client_id = member.id)
  //<form  method="post">
  let profile_form = document.getElementById('profile_form');
  send_url= "/message/"+client_json.id+"/send";
  profile_form.setAttribute("action",send_url);

  //<div id="client_profile">
  let client_profile = document.getElementById('client_profile');
  //   <label>Message Client: </label>
  // put a profile of our selected client here with javascript 
  profile_string = client_json.firstname+" "+client_json.lastname+" ("+client_json.dob+")";
  let name_par = document.createElement("p"); 
  const profileContent = document.createTextNode(profile_string);
  name_par.appendChild(profileContent);
  client_profile.appendChild(name_par);
 
}


/////////////////////////////////////////////
// create a radio button form to select a client from a short list
// given a list of sms_client() as json
function AddSelectElement(client_list_json){ 
  //<div id="profile_form" style="display: none;">
  let select_block = document.getElementById('select_block');
  select_block.setAttribute("style", "display: block;");

  // set competeing blocks to display:none
  let profile_block = document.getElementById('profile_block');
  profile_block.setAttribute("style", "display: none;");
  let search_block = document.getElementById('search_block');
  search_block.setAttribute("style", "display: none;");

  //let select_form = document.getElementById('select_form');
  let input_label, profile_string, input_el, for_radio, br_el;
  let client_select = document.getElementById('client_select');

  client_list_json.forEach(function(client) {
    br_el = document.createElement("br"); 
    client_select.appendChild(br_el);
    profile_string = client.firstname+" "+client.lastname+" ("+client.dob+")";
    input_label = document.createElement("label"); 
    profileContent = document.createTextNode(profile_string);
    input_label.appendChild(profileContent);
    for_radio = "radio_"+String(client.id);
    input_label.setAttribute("for",for_radio);

    input_el = document.createElement("input"); 
    input_el.setAttribute("type", "radio");
    input_el.setAttribute("id", for_radio);
    input_el.setAttribute("name", "client_id");
    input_el.setAttribute("value", client.id);
  
    client_select.appendChild(input_el);
    client_select.appendChild(input_label);
    });
  }
/////////////////////////////////////////////
// clear text message on submit
function submitFormAndReset(parentForm){ 
  document.getElementById(parentForm).submit();
  document.getElementById(parentForm).reset();
  }
/////////////////////////////////////////////
// form on submit
function submitFormAndHide(parentForm){ 
  document.getElementById(parentForm).submit();
  document.getElementById(parentForm).setAttibute("style","display: none;");
  }
