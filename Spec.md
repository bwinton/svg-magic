SVG Tool Spec.
==============

### Table of Contents
* [Reasoning](#reasoning)
* [Command Line Usage](#commandlineusage)
* [Input](#input)
* [Output](#output)
* [Architecture](#architecture)
* [Future features](#futurefeatures)


### Reasoning

Our Visual Design team spends a lot of time creating a set of sizes and
flavours of each image they come up with, for us to use on the various
platforms we support.  This process is tedious, extremely time-consuming,
and highly-automatable.  Normally, we would just hire an intern for stuff
like that, but in a dramatic twist of fate, we have decided to write a
tool to do the job instead!  :wink:


### Command Line Usage

```
usage: magic.py [-h] [-o OUTPUT] baseDir

A tool to merge svg files, and generate pngs.

positional arguments:
  baseDir               The directory to find the images and the manifests in.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        The directory to store the output in.
```


### Input

The `baseDir`, or input directory, needs to have the following structure:

`\sprites.mf`
: This is the manifest file, which details the files to load, and what
spritesheet they should be in.
: It has the following format:
```
icon1.svg spritesheet
icon2.svg spritesheet
```

`\icon1.svg`
`\icon2.svg`
: These files contain the SVG paths for each icon.
: Each file should have a
`<?xml-stylesheet type="text/css" href="stylesheet.css" ?>` line that
points at a stylesheet which will contain the platform-specific styles
for the icons.
: Each file should also have a `<use xlink:href="defs.svg#defs"/>` line
that points at a defs file which will contain the platform-specific
definitions (gradients/filters/etc…) for the icons.


`\OS X\defs.svg`
: This per-platform file will contain the platform-specific definitions
(gradients/filters/etc…) for the icons, and will be inserted into each
spritesheet.

`\OS X\stylesheet.css`
: This per-platform file will contain the platform-specific styles
for the icons, and will be inserted into each
spritesheet.

`\OS X\icon2.svg`
: This file will contain a platform-specific override for the SVG path
for a base icon.


### Output

The output directory, which will be created if it doesn’t exist, will have the following structure:

`\OS X\spritesheet.svg`
: The merged SVG file.
: It will be of the form:
```
<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
                     "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" version="1.1"
     x="0" y="0" height="16" width="32" viewbox="0 0 16 32">
  <style><![CDATA[
// Stylesheet data goes here.  One style element per included stylesheet.
]]></style>
  <defs>
<!-- Included definitions go here. -->
  </defs>
<!-- Merged icon group elements go here. -->
</svg>
```

`\OS X\spritesheetSprites.inc`
: The css include file.
: It will be of the form:
```
%define icon1-image list-style-image: url("chrome://browser/skin/spritesheet.svg");-moz-image-region: rect(0px, 16px, 16px, 0px);
%define icon1-hover -moz-image-region: rect(16px, 16px, 32px, 0px);
%define icon1-active -moz-image-region: rect(32px, 16px, 48px, 0px);
```


### Architecture

* The `Image` class is responsible for reading and parsing the svg files.
    * It contains `styles`, `uses`, `children`, `width`, and `height`.
* The `Spritesheet` class is responsible for holding a list of `Image`
  objects, and writing out the files for each platform.
    * There is one `Spritesheet` per, uh, spritesheet listed in the
      `sprites.mf` file.
    * The `Spritesheet` gets customized with a `Variant`, to get the actual
      files that we need to read in.
* The `Variant` class is responsible for getting the (possibly-overridden)
  files for each platform.
* Control flow:
    * The `processManifest` method parses the manifest and creates a list of
      `Spritesheet` objects.
    * The `getVariants` method looks in the subdirectories of the input
      directory, and creates a list of `Variant` objects.
    * For each `Variant`, we make the spritesheets for that variant.
        * For each `Spritesheet`, we get a new `Variant`-specified
          `Spritesheet`, and then tell that `Variant`-specified `Spritesheet`
          to write out the `Variant`-specific files.

### Future features

* We would like the option to write out merged png files instead of merged svg
  files, both for Fennec, and as a backup if the SVG handling on Firefox
  Desktop isn't fast enough.
* For Fennec, and for Desktop pngs, we'ld also like to figure out what to do
  about different sized icons.
