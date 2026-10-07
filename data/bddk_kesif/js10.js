
(function ($) {
	$.fn.vmenuModule = function (option) {
		var obj,
			item;
		var options = $.extend({
			Speed: 220,
			autostart: true,
			autohide: 1
		},
			option);
		obj = $(this);

		item = obj.find("ul").parent("li").children("a");
		item.attr("data-option", "off");

		item.unbind('click').on("click", function () {
			var a = $(this);
			if (options.autohide) {
				a.parent().parent().find("a[data-option='on']").parent("li").children("ul").slideUp(options.Speed / 1.2,
					function () {
						$(this).parent("li").children("a").attr("data-option", "off");
					})
			}
			if (a.attr("data-option") == "off") {
				a.parent("li").children("ul").slideDown(options.Speed,
					function () {
						a.attr("data-option", "on");
					});
			}
			if (a.attr("data-option") == "on") {
				a.attr("data-option", "off");
				a.parent("li").children("ul").slideUp(options.Speed)
			}
		});

		//alert(window.location.pathname);

		$gelenMenu = $(".u-vmenu a[href='" + window.location.pathname + "']");
		//alert($gelenMenu.parents('ul').parent('li').find('a[data-option="off"]').html());

		$gelenMenu.parents('ul').parent('li').find('a[data-option="off"]').attr('data-option', 'on');
		$gelenMenu.parents('ul').parent('li').find('a[data-option="on"]').next('ul').show();

		//if ($gelenMenu.parent("a").attr('data-option') == "off") {
		//    $gelenMenu.parent("a").attr('data-option', 'on');
		//    $gelenMenu.parent("ul").show();
		//}

		if (options.autostart) {
			obj.find("a").each(function () {

				$(this).parent("li").parent("ul").slideDown(options.Speed,
					function () {
						$(this).parent("li").children("a").attr("data-option", "on");
					})
			})
		}

	}
})(window.jQuery || window.Zepto);