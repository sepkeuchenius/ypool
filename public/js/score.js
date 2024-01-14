const match_loader = new Loader($("#match-table"))
const score_loader = new Loader($("#score-table"))
const bar_loader = new Loader($("#bar-container"))
var getElos;
var getBarChart;
document.addEventListener('DOMContentLoaded', function () {
    const getScore = firebase.functions().httpsCallable('get_score');
    getElos = firebase.functions().httpsCallable('get_elo_ratings');
    getBarChart = firebase.functions().httpsCallable('get_bar_chart');
    firebase.auth().onAuthStateChanged(function (loadedUser) {
        if (loadedUser) {
            getScore().then(function (matches) {
                for (_match of matches.data) {
                    $("#match-table").append(`<tr><td>${_match.winner}</td><td>${_match.loser}</td><td>${_match.issuer}</td>`)
                }
                $("#match-table td, #score-table td").each(function (el) {
                    if ($(this).text().includes(loadedUser.displayName)) {
                        $(this).css("color", "var(--blue)")
                    }
                })
                match_loader.stopLoader()
            });
            getElos().then(function (res) {
                for (score_i in res.data) {
                    const [name, elo] = res.data[score_i]
                    $("#score-table").append(`<tr><td>${Number(score_i) + 1}. ${name}</td><td>${Number(elo).toFixed(2)}</td>`)
                }

                $("#match-table td, #score-table td").each(function (el) {
                    if ($(this).text().includes(loadedUser.displayName)) {
                        $(this).css("color", "var(--blue)")
                    }
                })
                score_loader.stopLoader()
            })
            getBarChart().then((res) => {
                const data = {
                    labels: res.data.labels,
                    datasets: res.data.sets,
                };
                const config = {
                    type: 'bar',
                    data: data,
                    options: {
                        plugins: {
                            title: {
                                display: true,
                                text: 'Stats'
                            },
                        },
                        // responsive: true,    
                        interaction: {
                            intersect: false,
                        },
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                              stacked: true,
                            },
                            y: {
                              stacked: true
                            }
                          }
                    }
                };
                const ctx = document.getElementById('bar');
                new Chart(ctx, config)
                bar_loader.stopLoader()


            })

        }
    })
});
