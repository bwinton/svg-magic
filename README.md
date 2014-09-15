svg-magic
=========

A tool to merge svg files, and generate pngs.

### SVG Tool Spec. ###

Bug:
  [svg-magic](https://bugzilla.mozilla.org/show_bug.cgi?id=svg-magic)

Whiteboard notes:
  [Dropbox](https://www.dropbox.com/s/3wv3g0979fz50o4/2014-09-03%2016.18.32%20HDR.jpg?dl=0)

-moz-image-region is based on canvas-size not viewbox.
  therefore retina will just work

  `toolbarSprites.inc` (generated):
  ```
  %define whateverButton list-style-image: url("chrome://browser/skin/toolbars.svg");-moz-image-region: rect(0, 14px, 10px, 0);
  %define whateverHover -moz-image-region: rect(0, 14px, 10px, 10px);
  %define whateverActive -moz-image-region: rect(0, 14px, 10px, 20px);
  ```

  `toolbar.css`:
  ```
  %include toolbarSprites.inc
  %filter substitution
  …
  .whateverButton {
    @whateverButton@
    margin: 0;
  }
  .whateverButton:hover {
    @whateverHover@
    margin: 0;
  }
  .whateverButton:active {
    @whateverActive@
    margin: 0;
  }
  ```


`<use xlink:href="external.svg#someotherthing"/>`

* I need to load the external files and put the defs at the top.
* And delete the use statement.

Toolbar.def and Loop.def

* One def file (as above) per spritesheet, named the same.

Need to figure out hover somehow.

* Maybe just do the different styles on the sprites?


Python:
[ElementTree](https://docs.python.org/2/library/xml.etree.elementtree.html#module-xml.etree.ElementTree)


Converting to PNG:

* Node:
    * https://www.npmjs.org/package/svg-to-png
    * https://www.npmjs.org/package/svg2png
        * Uses PhantomJS
        * http://phantomjs.org/
* Python:
    * http://cairosvg.org/
    * http://cairographics.org/pycairo/
    * https://github.com/SimonSapin/cairocffi



Breakdown!!!!

* Write out spec.
* Implement manifest reader.
    * Add warnings for missing files.
* Implement SVG finder/loader.
* Implement SVG href-collecter/importer.
* Implement multi-SVG merger.
* Implement CSS generator.
* Figure out what to do on hover.
    * Separate def files?
    * Auto-generate hover styles on everything?
    * Some marker in the manifest?
* (v1.1/Android) Figure out what to do about different sizes.
* (v1.1/Android) Implement SVG->PNG conversion.
