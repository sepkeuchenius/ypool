
function match(){
    const getAllUsers = firebase.functions().httpsCallable('get_all_users');
    const saveMatch = firebase.functions().httpsCallable('save_match');
    outcome = $("input[name='outcome']").val()
    opponent = $("#opponent").val()
    saveMatch({"opponent":opponent, "outcome":outcome}).then((res)=>{if(res.data == "OK"){window.location.replace("/score")}});
}

document.addEventListener('DOMContentLoaded', function () {
    const getAllUsers = firebase.functions().httpsCallable('get_all_users');
    const saveMatch = firebase.functions().httpsCallable('save_match');
    GetAllUsers = firebase.functions().httpsCallable('get_all_users');
    firebase.auth().onAuthStateChanged(function (loadedUser) {
        if (loadedUser) {
            GetAllUsers().then(function (users) {
                console.log(users)
                for (user of users.data){
                    $("#opponent").append('<option value="'+user.uid+'">'+user.name+'</option>')
                }
            });
            
        } 
    })
});
