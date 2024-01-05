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
});

    function login() {
        var email = document.getElementById('email').value;
        var password = document.getElementById('password').value;

        firebase.auth().signInWithEmailAndPassword(email, password)
            .then((userCredential) => {
                // Signed in
                var user = userCredential.user;
                console.log("User logged in:", user);
                // Redirect or perform additional actions after successful login
            })
            .catch((error) => {
                var errorCode = error.code;
                var errorMessage = error.message;
                console.error("Login error:", errorMessage);
                // Handle login error (display a message to the user, etc.)
            });
    }