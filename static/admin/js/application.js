
$(document).ready(function(){
    //connect to the socket server.
    var socket = io.connect('http://' + document.domain + ':' + location.port + '/test');
    var numbers_received = [];

    //receive details from server
    socket.on('newnumber', function(msg) {
        console.log("Received number" + msg.number);

        final_string = msg.number

        if (typeof msg.user  !== 'undefined') {
            final_string = msg.number + '<br/>' + '<br/>' + 'Current User : ' + msg.user + '<br/>' + '<br/>' + 'Countdown : ' + msg.countdown + '<br/>'
        }

        $('#log').html(final_string);
    });

});