const loader = new Loader($("#form"))

function match() {
    loader.startLoader()
    const saveMatch = functions.httpsCallable('save_match');
    outcome = $("input[name='outcome']:checked").val()
    opponent = $("#opponent").val()
    saveMatch({ "opponent": opponent, "outcome": outcome }).then((res) => {
        if (res.data == "OK") { window.location.replace("/score") }
        else { alert("something went wrong"); loader.stopLoader() }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    GetAllUsers = functions.httpsCallable('get_all_users');
    firebase.auth().onAuthStateChanged(async function (loadedUser) {
        if (loadedUser) {
            await requestNotificationPermission()
            loader.pauseLoader()
            GetAllUsers().then(function (users) {
                console.log(users)
                for (user of users.data) {
                    $("#opponent").append('<option value="' + user.uid + '">' + user.name + '</option>')
                }
            });
        }
    })
});