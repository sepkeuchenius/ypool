var functions;
class Loader{
    constructor(div, init=true){
        this.div = div;
        this.prepareLoader()
        if(init){
            this.startLoader()
        }
    }
    prepareLoader(){
        this.loadDiv = this.div.clone()
        this.loadDiv.empty()
        this.loadDiv.hide()
        var img = $('<img>')
        img.attr('src', 'assets/loading.gif')
        img.css("margin", "0 auto")
        img.css("width", "50px")
        img.css("margin-left", "calc(50% - 25px)")
        img.css("margin-top", "calc(25% - 25px)")
        this.loadDiv.append(img)
        this.loadDiv.css("padding", "0")
        this.loadDiv.css("height", this.div.outerHeight())
        this.loadDiv.insertAfter(this.div)
        // this.div.parent().append(this.loadDiv)
    }

    startLoader(){
        this.loadDiv.css("height", this.div.outerHeight())
        this.div.hide();
        this.loadDiv.show();
    }
    pauseLoader(){
        this.loadDiv.hide();
        this.div.show();
    }
    stopLoader(){
        this.loadDiv.remove();
        this.div.show()
    }
}

var registerToken;

document.addEventListener('DOMContentLoaded', function () {
    functions = firebase.app().functions("europe-west1");
    if(window.location.href.includes("localhost")){
        functions.useEmulator("0.0.0.0", 5001)
    }
    registerToken = functions.httpsCallable('register_token');
});

function requestNotificationPermission() {
    console.log('Requesting permission...');
    Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
            console.log('Notification permission granted.');
            const messaging = firebase.messaging()
            return messaging.getToken({ vapidKey: 'BMe2ouKwxdv2lZn23AO95IuEC1UKj7Pr03pbDPaOOF66sEqEyie_slj7MDkWdldXb4NaZJZBeEbEE0KqiNiul-o' }).then((currentToken) => {
                if (currentToken) {
                    console.log(currentToken)
                    messaging.onMessage(message)
                    registerToken({ "token": currentToken });
                } else {
                    console.log('No registration token available. Request permission to generate one.');
                }
            }).catch((err) => {
                console.log('An error occurred while retrieving token. ', err);
            });
        }
        else {
            console.log("Notification permission not granted")
        }
    })
}

function getNotificationToken(){
    Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
            console.log('Notification permission granted.');
            const messaging = firebase.messaging()
            return messaging.getToken({ vapidKey: 'BMe2ouKwxdv2lZn23AO95IuEC1UKj7Pr03pbDPaOOF66sEqEyie_slj7MDkWdldXb4NaZJZBeEbEE0KqiNiul-o' }).then((currentToken) => {
                if (currentToken) {
                    console.log(currentToken)
                } else {
                    console.log('No registration token available. Request permission to generate one.');
                }
            }).catch((err) => {
                console.log('An error occurred while retrieving token. ', err);
            });
        }
        else {
            console.log("Notification permission not granted")
        }
    })
}


function message(payload) {
    navigator.serviceWorker.register('firebase-messaging-sw.js');
    navigator.serviceWorker.ready.then(function (registration) {
        const notificationTitle = payload.data.title || 'Default Title';
        const notificationOptions = {
            body: payload.data.body || 'Default Body',
            icon: 'assets/ypool.svg', // Set the path to your notification icon
            image: 'assets/ypool.svg', // Set the path to your notification icon
            silent: false,
            data: { url: "https://pool.chatbots.nl" }, //the url which we gonna use later
            actions: [{ action: "open_url", title: "Read" }]
        };

        registration.showNotification(notificationTitle, notificationOptions);
    });
}
