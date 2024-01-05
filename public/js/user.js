document.addEventListener('DOMContentLoaded', function () {
    createUserAccount = firebase.functions().httpsCallable('create_user_account');
    window.setTimeout(() => {
        firebase.functions().useEmulator("localhost", 5001);
        firebase.auth().onAuthStateChanged(function (loadedUser) {
            if (loadedUser) {
                console.log(loadedUser)
                createUserAccount({"username": loadedUser.displayName});
                $("#username").text(loadedUser.displayName)
            } 
        })

    })
});
