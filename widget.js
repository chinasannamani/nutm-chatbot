/*
 * NUTM Assistant - embeddable chat widget.
 *
 * To add it to any web page, paste ONE line before </body>:
 *   <script src="https://YOUR-CHATBOT-URL/widget.js"></script>
 * Add data-open="true" to start with the chat window open.
 * The widget sends questions to YOUR-CHATBOT-URL/chat (the same server that serves this file).
 *
 * Buttons in the chat header:
 *   "–"  minimize: shrinks the chat to just its title bar (click the bar to expand again)
 *   "×"  close: hides the chat and brings back the round NUTM bubble (conversation is kept)
 */
(function () {
  var script = document.currentScript;
  var API = new URL("/chat", script.src).href;
  var ICON = new URL("/nutm_icon.png", script.src).href;
  var startOpen = script.getAttribute("data-open") === "true";

  var css = `
  #nutm-bot *{box-sizing:border-box;font-family:Arial,Helvetica,sans-serif}
  #nutm-bot-btn{position:fixed;right:16px;bottom:16px;width:54px;height:54px;border-radius:50%;
    background:#fff;padding:0;overflow:hidden;border:3px solid #009f5d;cursor:pointer;
    box-shadow:0 4px 14px rgba(0,0,0,.3);z-index:99999}
  #nutm-bot-btn img{width:100%;height:100%;display:block}
  #nutm-bot-panel{position:fixed;right:16px;bottom:16px;width:310px;max-width:calc(100vw - 32px);
    height:400px;max-height:calc(100vh - 32px);background:#fff;border-radius:12px;
    box-shadow:0 8px 28px rgba(0,0,0,.3);display:none;flex-direction:column;overflow:hidden;z-index:99999}
  #nutm-bot-panel.open{display:flex}
  #nutm-bot-panel.min{height:auto}
  #nutm-bot-panel.min #nutm-bot-msgs,#nutm-bot-panel.min #nutm-bot-form{display:none}
  #nutm-bot-head{background:#fff;color:#222;padding:8px 10px;font-weight:bold;font-size:14px;display:flex;
    align-items:center;gap:10px;border-bottom:3px solid #009f5d;cursor:default}
  #nutm-bot-panel.min #nutm-bot-head{cursor:pointer;border-bottom:none}
  #nutm-bot-head img{width:34px;height:34px;border-radius:6px;flex:none}
  #nutm-bot-title{flex:1;min-width:0}
  #nutm-bot-title small{display:block;font-weight:normal;color:#555;font-size:11px;margin-top:1px}
  .nb-ctl{background:none;border:none;color:#555;font-size:20px;line-height:1;width:28px;height:28px;
    border-radius:6px;cursor:pointer;flex:none}
  .nb-ctl:hover{background:#e8f5ee;color:#009f5d}
  #nutm-bot-msgs{flex:1;overflow-y:auto;padding:10px;background:#f4f6f5}
  .nb-msg{max-width:88%;padding:7px 10px;margin:5px 0;border-radius:12px;font-size:13px;
    line-height:1.4;white-space:pre-wrap;word-wrap:break-word}
  .nb-bot{background:#fff;color:#222;border:1px solid #dde3e0;border-bottom-left-radius:3px}
  .nb-user{background:#009f5d;color:#fff;margin-left:auto;border-bottom-right-radius:3px}
  #nutm-bot-form{display:flex;border-top:1px solid #dde3e0}
  #nutm-bot-input{flex:1;border:none;padding:11px 12px;font-size:13px;outline:none;min-width:0}
  #nutm-bot-send{background:#fff;border:none;color:#009f5d;font-weight:bold;padding:0 14px;cursor:pointer}
  `;
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var root = document.createElement("div");
  root.id = "nutm-bot";
  root.innerHTML =
    '<div id="nutm-bot-panel">' +
    '<div id="nutm-bot-head"><img src="' + ICON + '" alt="NUTM logo">' +
    '<div id="nutm-bot-title">NUTM Assistant<small>Programmes, fees and admission</small></div>' +
    '<button class="nb-ctl" id="nutm-bot-min" title="Minimize" aria-label="Minimize chat">&#8211;</button>' +
    '<button class="nb-ctl" id="nutm-bot-close" title="Close" aria-label="Close chat">&#215;</button></div>' +
    '<div id="nutm-bot-msgs"></div>' +
    '<div id="nutm-bot-form"><input id="nutm-bot-input" placeholder="Type your question..." autocomplete="off">' +
    '<button id="nutm-bot-send">Send</button></div></div>' +
    '<button id="nutm-bot-btn" title="Chat with NUTM Assistant"><img src="' + ICON + '" alt="NUTM"></button>';
  document.body.appendChild(root);

  var panel = root.querySelector("#nutm-bot-panel");
  var bubble = root.querySelector("#nutm-bot-btn");
  var msgs = root.querySelector("#nutm-bot-msgs");
  var input = root.querySelector("#nutm-bot-input");
  var minBtn = root.querySelector("#nutm-bot-min");

  function add(text, who) {
    var d = document.createElement("div");
    d.className = "nb-msg " + (who === "user" ? "nb-user" : "nb-bot");
    d.textContent = text; // textContent keeps it safe from HTML injection
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  function send() {
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    add(text, "user");
    var thinking = add("...", "bot");
    fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) { thinking.textContent = data.reply; msgs.scrollTop = msgs.scrollHeight; })
      .catch(function () {
        thinking.textContent = "Sorry, I cannot reach the chatbot server right now.";
      });
  }

  function openChat() {
    panel.classList.add("open");
    panel.classList.remove("min");
    bubble.style.display = "none";
    minBtn.innerHTML = "&#8211;";
    input.focus();
    msgs.scrollTop = msgs.scrollHeight;
  }
  function closeChat() {
    panel.classList.remove("open", "min");
    bubble.style.display = "block";
  }
  function setMinimized(min) {
    panel.classList.toggle("min", min);
    minBtn.innerHTML = min ? "&#9633;" : "&#8211;";
    minBtn.title = min ? "Expand" : "Minimize";
    if (!min) { input.focus(); msgs.scrollTop = msgs.scrollHeight; }
  }

  bubble.onclick = openChat;
  root.querySelector("#nutm-bot-close").onclick = closeChat;
  minBtn.onclick = function (e) { e.stopPropagation(); setMinimized(!panel.classList.contains("min")); };
  // clicking the title bar while minimized expands the chat again
  root.querySelector("#nutm-bot-head").onclick = function () {
    if (panel.classList.contains("min")) setMinimized(false);
  };
  root.querySelector("#nutm-bot-send").onclick = send;
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") send(); });

  add("Hello! I'm the NUTM Assistant. Ask me about programmes, fees, admission or contacts.", "bot");
  if (startOpen) openChat();
})();
