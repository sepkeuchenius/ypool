function match(){
    saveMatch = firebase.functions().httpsCallable('save_match');
    saveMatch({"winner":$("#winner").val(), "loser":$("#loser").val()}).then((res)=>{console.log(res)});
}