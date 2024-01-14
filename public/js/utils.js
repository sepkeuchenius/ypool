class Loader{
    constructor(div, init=true){
        this.div = div;
        this.prepareLoader()
        if(init){
            this.startLoader()
        }
    }
    prepareLoader(){
        this.loadDiv = this.div.clone()
        this.loadDiv.empty()
        this.loadDiv.hide()
        var img = $('<img>')
        img.attr('src', 'assets/loading.gif')
        img.css("margin", "0 auto")
        img.css("width", "50px")
        img.css("margin-left", "calc(50% - 25px)")
        img.css("margin-top", "calc(25% - 25px)")
        this.loadDiv.append(img)
        this.loadDiv.css("padding", "0")
        this.loadDiv.css("height", this.div.outerHeight())
        this.loadDiv.insertAfter(this.div)
        // this.div.parent().append(this.loadDiv)
    }

    startLoader(){
        this.loadDiv.css("height", this.div.outerHeight())
        this.div.hide();
        this.loadDiv.show();
    }
    pauseLoader(){
        this.loadDiv.hide();
        this.div.show();
    }
    stopLoader(){
        this.loadDiv.remove();
        this.div.show()
    }
}