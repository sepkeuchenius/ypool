document.addEventListener('DOMContentLoaded', function () {
    createUserAccount = firebase.functions().httpsCallable('create_user_account');
    window.setTimeout(() => {
        firebase.auth().onAuthStateChanged(function (loadedUser) {
            if (loadedUser) {
                console.log(loadedUser);
                createUserAccount({"username": loadedUser.displayName});
                $("#username").text(loadedUser.displayName)
            } 
        })

    })
});
