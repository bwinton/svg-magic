#! /usr/bin/env python
# coding=utf-8

import argparse
from clint.textui.colored import red, green, blue
from clint.textui import progress
import copy
import csv
import io
from lxml import etree
import os
import subprocess
import sys
from time import sleep


SPRITESHEET_SVG = io.BytesIO('''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
                     "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">

<svg version="1.1"
     xmlns="http://www.w3.org/2000/svg"
     x="0"
     y="0">
</svg>''')

EXTRA_CLASSES = '{http://www.w3.org/2000/svg}extra-classes'
EXTRA_THEME = '{http://www.w3.org/2000/svg}extra-theme'
EXTRA_TAGS = [EXTRA_CLASSES, EXTRA_THEME]


class Usage(Exception):
    def __init__(self, msg, data):
        self.msg = msg
        self.data = data


def processManifest(args):
    manifestPath = os.path.join(args.baseDir, 'sprites.mf')
    if not os.path.exists(manifestPath):
        raise Usage('Manifest not found at %s.' %
                    (red(manifestPath, bold=True)),
                    (manifestPath,))
    lineCount = len(open(manifestPath).readlines())

    manifest = csv.DictReader(open(manifestPath), skipinitialspace=True)
    manifest.fieldnames = ['filename', 'spritesheet']
    spritesheets = {}

    for line in progress.bar(manifest,
                             label='Reading Manifest: ',
                             expected_size=lineCount):
        sheet = line['spritesheet']
        image = line['filename']
        imagePath = os.path.join(args.baseDir, image)
        if not os.path.exists(imagePath):
            raise Usage('Image not found at %s from %s, %s.' %
                        (red(imagePath, bold=True),
                         blue(manifestPath, bold=True),
                         blue('line ' + str(manifest.line_num), bold=True)),
                        (imagePath, manifestPath, manifest.line_num))
        spritesheets.setdefault(sheet, Spritesheet(sheet)).addImage(image)
    return spritesheets.values()


class Image(object):
    def __init__(self, name, path):
        self.name = name.replace('.svg', '')
        self.path = path
        self.hasClass = False
        self.tree = etree.parse(self.path)
        self.parseTree()

    def __str__(self):
        return 'Image<' + self.path + '>'

    def __repr__(self):
        return self.__str__()

    def parseTree(self):
        # Get (and remove) the use statements.
        self.uses = self.tree.findall('{http://www.w3.org/2000/svg}use')
        for use in self.uses:
            use.getparent().remove(use)
        self.uses = [use.attrib['{http://www.w3.org/1999/xlink}href']
                     for use in self.uses]

        # Get the one remaining child;
        self.child = self.tree.getroot().getchildren()
        if len(self.child) != 1:
            raise Usage('More than one child in %s.' %
                        (red(self.path, bold=True),),
                        (self.path,))
        self.child = self.child[0]

        # And the width/height, and maybe the viewbox.
        attrib = self.tree.getroot().attrib
        self.width = int(attrib['width'])
        self.height = int(attrib['height'])


class Spritesheet(object):
    def __init__(self, name, images=None):
        self.name = name
        if images is None:
            images = []
        self.images = images
        self.isTheme = False

    def __str__(self):
        rv = 'Spritesheet<' + self.name
        if self.isTheme:
            rv += ':theme'
        rv += '>'
        return rv

    def __repr__(self):
        return self.__str__()

    def addImage(self, image):
        self.images.append(image)

    def loadStyle(self, style):
        data = open(style).read()
        return etree.CDATA('\n' + data + '\n')

    def loadDef(self, filename):
        tree = etree.parse(filename)
        defs = tree.getroot().getchildren()
        return defs

    def getAlternates(self, image):
        alternates = [image]
        seenClasses = set()
        for use in image.uses:
            for element in self.usemap[use]:
                if element.tag == EXTRA_CLASSES:
                    classes = element.attrib['value'].split()
                    for classname in classes:
                        if classname not in seenClasses:
                            seenClasses.add(classname)
                            alternate = copy.deepcopy(image)
                            alternate.child.attrib['class'] = classname
                            alternate.child.attrib['id'] += '-' + classname
                            alternate.name += '-' + classname
                            alternate.hasClass = True
                            alternates.append(alternate)

        return alternates

    def getStyles(self, uses):
        styles = []
        styleNames = set()
        for use in uses:
            tree = etree.parse(use)
            pi = tree.getroot()
            while pi is not None:
                if (isinstance(pi, etree._ProcessingInstruction) and
                        pi.target == 'xml-stylesheet' and
                        pi.attrib['type'] == 'text/css' and
                        pi.attrib['href'] not in styleNames):
                    styles.append(pi.attrib['href'])
                    styleNames.add(pi.attrib['href'])
                pi = pi.getprevious()
        return styles

    def getThemes(self, uses):
        themes = {}
        for use in uses:
            for element in use:
                if (element.tag == EXTRA_THEME):
                    # <extra-theme name="luna-blue" href="luna-blue.css"/>
                    themes[element.attrib['name']] = element.attrib['href']
        return themes

    def getVariants(self, variant):
        new = Spritesheet(self.name)
        styles = set()
        uses = set()
        for image in self.images:
            newImage = Image(image, variant.getFile(image))
            uses.update(newImage.uses)
            # print newImage.name, newImage.width, newImage.height

        # Get the stylesheets…
        styles = self.getStyles(variant.getFile(use) for use in uses)
        new.styles = [self.loadStyle(variant.getDefsFile(style))
                      for style in styles]

        new.usemap = {use: self.loadDef(variant.getDefsFile(use))
                      for use in uses}
        new.uses = [new.usemap[use] for use in sorted(uses)]

        for image in self.images:
            newImage = Image(image, variant.getFile(image))
            new.images.extend(new.getAlternates(newImage))
        variants = [new]

        new.themes = self.getThemes(new.uses)
        for theme, style in new.themes.items():
            alternate = copy.copy(new)
            alternate.name += '-' + theme
            alternate.isTheme = True
            alternate.styles = copy.copy(new.styles)
            style = variant.getDefsFile(style)
            alternate.styles.append(alternate.loadStyle(style))
            variants.append(alternate)

        return variants

    def write(self, output, png):
        imageExt = 'svg'
        if png:
            imageExt = 'png'

        tree = etree.parse(SPRITESHEET_SVG)
        root = tree.getroot()
        root.text = '\n\n  '

        for style in self.styles:
            styleElem = etree.Element('style')
            styleElem.text = style
            styleElem.tail = '\n\n  '
            root.append(styleElem)

        for use in self.uses:
            use = [element for element in use if element.tag not in EXTRA_TAGS]
            if len(use):
                use[-1].tail = '\n\n  '
            root.extend(use)

        height = 0
        width = 0
        for image in self.images:
            image.child.attrib['style'] = ('transform:translate(%dpx)'
                                           ) % (width,)
            root.append(image.child)
            image.child.tail = '\n  '
            image.offset = width
            width += image.width
            if image.height > height:
                height = image.height
        image.child.tail = '\n'

        root.attrib['height'] = '%d' % (height,)
        root.attrib['width'] = '%d' % (width,)
        root.attrib['viewbox'] = '0 0 %d %d' % (height, width)

        data = etree.tostring(tree,
                              xml_declaration=True,
                              encoding='utf-8')

        if not os.path.exists(output):
            os.makedirs(output)
        svgPath = os.path.join(output, self.name + '.svg')
        print 'Writing:', svgPath
        svg = open(svgPath, 'w')
        svg.write(data)
        svg.close()

        if not self.isTheme:
            # Write out the CSS!
            cssPath = os.path.join(output, self.name + 'Sprites.inc')
            print 'Writing:', cssPath
            css = open(cssPath, 'w')
            data = ''
            for image in self.images:
                if not image.hasClass:
                    data += '\n'
                    data += '%%define %s-sprite ' % (image.name,)
                    data += 'list-style-image: url("chrome:'
                    data += '//browser/skin/%s.%s");\n' % (self.name, imageExt)
                    for theme in self.themes:
                        data += '%%define %s-%s-sprite ' % (image.name, theme)
                        data += 'list-style-image: url("chrome://browser'
                        data += '/skin/%s-%s.%s");\n' % (self.name, theme,
                                                         imageExt)
                data += '%%define %s-image ' % (image.name,)
                data += '-moz-image-region: rect(0px, '
                data += '%dpx, %dpx, %dpx);\n' % (image.offset+image.width,
                                                  image.height, image.offset)
            data = data[1:]
            css.write(data)
            css.close()
        return self.name + '.svg'


class Variant(object):
    def __init__(self, variantDir, args):
        self.variantDir = variantDir
        self.baseDir = args.baseDir
        self.png = args.png
        self.output = os.path.join(args.output, self.variantDir)
        self.svgs = []

    def __str__(self):
        return 'Variant<' + self.variantDir + '>'

    def __repr__(self):
        return self.__str__()

    def getFile(self, filename):
        filePath = os.path.join(self.baseDir, self.variantDir, filename)
        if os.path.exists(filePath):
            return filePath
        baseFilePath = os.path.join(self.baseDir, filename)
        if not os.path.exists(baseFilePath):
            return filePath
        return baseFilePath

    def getDefsFile(self, filename):
        filePath = self.getFile(filename)
        return filePath

    def make(self, spritesheets):
        print
        # Get images in spritesheet for variant…
        for spritesheet in spritesheets:
            sheets = spritesheet.getVariants(self)
            for sheet in sheets:
                self.svgs.append(os.path.join(self.variantDir,
                                              sheet.write(self.output,
                                                          self.png)))


def getVariants(args):
    variants = os.walk(args.baseDir).next()[1]
    variants = [Variant(variant, args) for variant in variants]
    if len(variants) == 0:
        raise Usage('No subdirectory-based variants found in %s.' %
                    (blue(args.baseDir, bold=True),),
                    (args.baseDir,))
    return variants


def makePngs(output, variants):
    print
    print "Writing pngs to " + output + "/"
    htmlPath = os.path.join(output, 'svgs.html')
    html = open(htmlPath, 'w')
    html.write("""<!doctype html>
<html><head>
<meta charset="utf-8">
<title>Testing</title>
<style>
* {
  padding: 0;
  margin: 0;
}
</style>
</head>
<body>

""")
    for variant in variants:
        for svg in variant.svgs:
            html.write('<img src="' + svg + '">\n')
    html.write("""
</body>
</html>""")
    html.close()
    subprocess.call([
        'node_modules/.bin/slimerjs',
        'converter.js',
        os.path.abspath(htmlPath),
        os.path.abspath(output),
        '1'])
    os.remove(htmlPath)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        parser = argparse.ArgumentParser(
            add_help=True,
            description='A tool to merge svg files, and generate pngs.'
        )
        parser.add_argument(
            'baseDir',
            help='The directory to find the images and the manifests in.')
        parser.add_argument(
            '-o', '--output',
            default='output',
            help='The directory to store the output in.')
        parser.add_argument(
            '-p', '--png',
            action="store_true",
            help='Generate PNG files.')
        args = parser.parse_args(argv[1:])
        spritesheets = processManifest(args)
        variants = getVariants(args)
        for variant in variants:
            variant.make(spritesheets)
        if args.png:
            makePngs(args.output, variants)
    except Usage, err:
        print >>sys.stderr
        print >>sys.stderr, red('Error:', bold=True)
        print >>sys.stderr, err.msg
        print >>sys.stderr
        print >>sys.stderr, green('for help use --help', bold=True)
        return 2

if __name__ == '__main__':
    sys.exit(main())
