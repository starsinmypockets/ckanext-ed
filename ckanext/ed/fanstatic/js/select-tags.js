$(document).ready(function() {
  var tagsToSelect = $('.select-multiple').attr("data-stags").split(',')
  $('.select-multiple').select2({tags: tagsToSelect});
});
