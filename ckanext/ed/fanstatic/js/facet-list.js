$('.usa-checkbox>input:checked').each(function(){
  $(this).parent()
         .prependTo(
           $(this).closest('ul')
         );
});
