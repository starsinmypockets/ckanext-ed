$('body').scrollspy({ target: '#spy', offset:280});


//Getting sidebar height
$(document).ready(function(){
    calcSidebarHeight();
});

$(window).resize(function(){
    calcSidebarHeight();
});

$(window).on('load',function(){
    calcSidebarHeight();
    calcScrollLocation();
});

$(window).scroll(function() {    
    calcScrollLocation();
}); 

function calcSidebarHeight(){
    var height = $(".module-content").outerHeight();
    $(".sidebar").height(height);
}

function calcScrollLocation(){
    var scroll = $(window).scrollTop();

     //>=, not <=
    if (scroll >= 90) {
        $('.sidebar_content_wrap').addClass("fixed");
    } else {
        $('.sidebar_content_wrap').removeClass("fixed");
    }
}