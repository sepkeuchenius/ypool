
function onBackgroundMessage() {
    const messaging = firebase.messaging().usePublicVapidKey(
      "BMe2ouKwxdv2lZn23AO95IuEC1UKj7Pr03pbDPaOOF66sEqEyie_slj7MDkWdldXb4NaZJZBeEbEE0KqiNiul-o"
    );;
  
    // [START messaging_on_background_message]
    messaging.onBackgroundMessage((payload) => {
      console.log(
        '[firebase-messaging-sw.js] Received background message ',
        payload
      );
      // Customize notification here
      const notificationTitle = 'Background Message Title';
      const notificationOptions = {
        body: 'Background Message body.',
        icon: '/firebase-logo.png'
      };
  
      self.registration.showNotification(notificationTitle, notificationOptions);
    });
    // [END messaging_on_background_message]
  }