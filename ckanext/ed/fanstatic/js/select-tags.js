$(document).ready(function() {

  if($('.select-multiple').length >0 ){
    //your code here 
    var tagsToSelect = $('.select-multiple').attr("data-stags").split(',')
    $('.select-multiple').select2({tags: tagsToSelect});
  }

  
});
