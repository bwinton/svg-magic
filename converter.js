"use strict";
/*global phantom: false*/

var webpage = require("webpage");

if (phantom.args.length !== 3) {
	console.error("Usage: converter.js source dest scale");
	phantom.exit();
} else {
	convert(phantom.args[0], phantom.args[1], phantom.args[2]);
}

var onError = function (msg, stack) {
    var msg = "\nScript Error: "+msg+"\n";
    if (stack && stack.length) {
        msg += "       Stack:\n";
        stack.forEach(function(t) {
            msg += '         -> ' + (t.file || t.sourceURL) + ': ' + t.line + (t.function ? ' (in function ' + t.function + ')' : '')+"\n";
        })
    }
    console.error(msg+"\n");
    phantom.exit();
}

phantom.onError = onError;

function convert(source, dest, scale) {
	var page = webpage.create();
  page.onError = onError;
  page.onLoadFinished = function (status, url, isFrame) {
    var dimensions = getSvgDimensions(page);
    console.log(JSON.stringify(dimensions));

    setTimeout(function() {
      for (let dimension of dimensions) {
        page.clipRect = dimension;
        console.log("Rendering to " + dest + '/' + dimension.name);
        page.render(dest + '/' + dimension.name);
      }
      phantom.exit();
    }, 0);
  };

	page.open(source, function (status, arg) {
		if (status !== "success") {
			console.error("Unable to load the source file.");
			phantom.exit();
			return;
		}
	});
}

function getSvgDimensions(page) {
	var rv = page.evaluate(function () {
		var images = document.documentElement.querySelectorAll("img");
    var dimensions = [];
    for (let image of images) {
      var bbox = image.getBoundingClientRect();
      dimensions.push({
        name: image.getAttribute('src').replace('.svg', '.png'),
        top: bbox.y, left: bbox.x,
        width: bbox.width, height: bbox.height});
    }
    return dimensions;
	});
  return rv;
}
