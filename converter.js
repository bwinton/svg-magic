'use strict';
/*global phantom: false*/

var webpage = require('webpage');

if (phantom.args.length !== 4) {
	console.error('Usage: converter.js source dest suffix scale');
	phantom.exit();
} else {
	convert(phantom.args[0], phantom.args[1], phantom.args[2], +phantom.args[3]);
}

var onError = function (msg, stack) {
    var msg = '\nScript Error: '+msg+'\n';
    if (stack && stack.length) {
        msg += '       Stack:\n';
        stack.forEach(function(t) {
            msg += '         -> ' + (t.file || t.sourceURL) + ': ' + t.line + (t.function ? ' (in function ' + t.function + ')' : '')+'\n';
        })
    }
    console.error(msg+'\n');
    phantom.exit();
}

phantom.onError = onError;

function convert(source, dest, suffix, scale) {
	var page = webpage.create();
  page.onError = onError;
  page.onLoadFinished = function (status, url, isFrame) {
    page.zoomFactor = scale;
    var dimensions = getSvgDimensions(page, suffix);

    setTimeout(function() {
      for (let dimension of dimensions) {
        page.clipRect = dimension;
        console.log('Rendering to ' + dest + '/' + dimension.name);
        page.render(dest + '/' + dimension.name);
      }
      phantom.exit();
    }, 500);
  };

	page.open(source, function (status, arg) {
		if (status !== 'success') {
			console.error('Unable to load the source file.');
			phantom.exit();
			return;
		}
	});
}

function getSvgDimensions(page, suffix) {
  var zf = page.zoomFactor;
	var rv = page.evaluate(function () {
    var images = document.documentElement.querySelectorAll('img');
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
  rv = rv.map(i => {
    i.name = i.name.replace('.png', suffix + '.png');
    i.top *= page.zoomFactor;
    i.left *= page.zoomFactor;
    i.width *= page.zoomFactor;
    i.height *= page.zoomFactor;
    return i;
  });
  return rv;
}
