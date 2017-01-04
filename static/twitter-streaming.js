// websocket connection
function startStream(retry, delay) {
  var stream = new WebSocket("ws://"+document.location.host+"/stream/twitter");
  stream.onopen = function() {
    console.log("stream connected");
  };
  stream.onerror = function() {
    console.log("stream disconnected, retrying");
    if (retry-- > 0) {
      setTimeout(function() { startStream(retry, delay); }, delay);
    }
  };
  stream.onmessage = function(json) {
    console.log(json);
    console.log(json.data);
  };
}

startStream(100, 2000);
