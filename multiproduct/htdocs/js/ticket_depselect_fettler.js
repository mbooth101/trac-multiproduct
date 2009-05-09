/* 
 * This script fettles depselect fields by hiding options whose parent option
 * is not selected.
 */

jQuery(document).ready(function($) {
	
	/* get a list of all depselect fields and their parent fields */
	/* TODO: don't hard code this list */
	var depselects = new Array();
	depselects.push(new Array("product_component","product"));
	depselects.push(new Array("product_version","product"));
	
	for(var i=0; i < depselects.length; i++) {
		
		/* parent field id */
		var par_field = "#field-" + depselects[i][1];
		
		/* ensure the parent field knows about all of its depselect children */
		var children = $(par_field).data("children");
		if (children == null)
			children = new Array();
		children.push(depselects[i][0]);
		$(par_field).data("children", children);
		
		/* add a change event to every parent field of a depselect field */
		$(par_field).change(function() {
			
			/* the elegant way to do this would be to just set the display style to 'none' on
			   options we don't want to see but IE's brain damaged CSS implementation prevents
			   that, so instead we resort to shuffling options to and from a secret seperate
			   select element */
			var parent = $(this).attr("id");
			var children = $(this).data("children");
			
			for(var j=0; j < children.length; j++) {
				
				/* remove all the options from the depselect and replace with options from the
				   secret select whose class matches the value selected in the parent field */
				$("#field-" + children[j] + " option").remove();
				$("#" + parent + children[j] + " option").filter(function(idx) {
					return ($(this).text() == "" || $(this).attr("class") == $("#" + parent).val());
				}).clone().appendTo($("#field-" + children[j]));
				
				/* set the default selected item to be the value in the ticket */
				var selIdx = 0;
				$("#field-" + children[j] + " option").filter(function(idx) {
					if($(this).text() == $("#" + parent + children[j] + " option:selected").text())
					selIdx = idx;
					return true;
				}).parent().attr("selectedIndex", selIdx);
			}
		}).change();
	}
});
