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
and highly-automatable; in other words, a perfect candidate to replace
with a tool!


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
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
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
### Future features
