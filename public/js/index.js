document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(() => {
        firebase.functions().useEmulator("localhost", 5001);
        firebase.auth().onAuthStateChanged(function (loadedUser) {
            if (loadedUser) {               
                window.location.replace("/user?id=" + loadedUser.uid)
                // loadUser({"user": loadedUser})
            } else {
                if (!(firebase.auth().currentUser)) {
                    var ui = new firebaseui.auth.AuthUI(firebase.auth());
                    ui.start('#firebaseui-auth-container', {
                        signInOptions: [
                            firebase.auth.EmailAuthProvider.PROVIDER_ID,
                        ],                      
                        signInSuccessURL: "/"
                    });
                }

            }
        })

    })
})