document.addEventListener('DOMContentLoaded', function () {
    GetAllUsers = firebase.functions().httpsCallable('get_all_users');
    firebase.auth().onAuthStateChanged(function (loadedUser) {
        if (loadedUser) {
            console.log("Test silvan");
            GetAllUsers().then(function (users) {
                console.log(users)
                for (user of users.data){
                    $("#users").append('<option value="'+user.uid+'">'+user.name+'</option>')
                }
            });
            
        } 
    })
});
