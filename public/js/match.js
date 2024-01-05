const getAllUsers = firebase.functions().httpsCallable('get_all_users');
const saveMatch = firebase.functions().httpsCallable('save_match');

function match(){
    outcome = $("input[name='outcome']").val()
    opponent = $("#opponent").val()
    saveMatch({"opponent":opponent, "outcome":outcome}).then((res)=>{console.log(res)});
}