document.addEventListener('DOMContentLoaded', function () {
    window.setTimeout(() => {
        firebase.functions().useEmulator("localhost", 5001);
        firebase.auth().onAuthStateChanged(function (loadedUser) {
            if (loadedUser) {
                console.log(loadedUser)
                $("#username").text(loadedUser.displayName)
            } 
        })

    })
});
