#! /usr/bin/env python
# coding=utf-8

import argparse
from clint.textui.colored import red, green, blue

from time import sleep
from clint.textui import progress
import csv
import io
import os
import sys
from lxml import etree


SPRITESHEET_SVG = io.BytesIO('''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
                     "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">

<svg version="1.1"
     xmlns="http://www.w3.org/2000/svg"
     x="0"
     y="0">
</svg>''')


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
        self.tree = etree.parse(self.path)
        self.parseTree()

    def __str__(self):
        return 'Image<' + self.path + '>'

    def __repr__(self):
        return self.__str__()

    def parseTree(self):
        # Get the stylesheets…
        self.styles = []
        pi = self.tree.getroot()
        while pi is not None:
            if (isinstance(pi, etree._ProcessingInstruction) and
                    pi.target == 'xml-stylesheet' and
                    pi.attrib['type'] == 'text/css'):
                self.styles.append(pi.attrib['href'])
            pi = pi.getprevious()

        # Get (and remove) the use statements.
        self.uses = self.tree.findall('{http://www.w3.org/2000/svg}use')
        for use in self.uses:
            use.getparent().remove(use)
        self.uses = [use.attrib['{http://www.w3.org/1999/xlink}href']
                     for use in self.uses]

        # Get the rest of the children.
        self.children = self.tree.getroot().getchildren()

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

    def __str__(self):
        return 'Spritesheet<' + self.name + '>'

    def __repr__(self):
        return self.__str__()

    def addImage(self, image):
        self.images.append(image)

    def loadStyle(self, style):
        data = open(style).read()
        return etree.CDATA('\n' + data + '\n')

    def loadDef(self, use):
        filename, xmlId = use
        tree = etree.parse(filename)
        defs = tree.find('*[@id="' + xmlId + '"]')
        return defs.getchildren()

    def getVariant(self, variant):
        new = Spritesheet(self.name, self.images[:])
        new.images = [Image(image, variant.getFile(image))
                      for image in new.images]

        styles = set()
        uses = set()
        for image in new.images:
            styles.update(image.styles)
            uses.update(image.uses)
            print image.name, image.width, image.height

        styles = [variant.getFile(sheet) for sheet in sorted(styles)]
        new.styles = [self.loadStyle(style) for style in styles]

        uses = [variant.getDefsFile(use) for use in sorted(uses)]
        new.uses = [self.loadDef(use) for use in uses]

        return new

    def write(self, output):
        tree = etree.parse(SPRITESHEET_SVG)
        root = tree.getroot()
        root.text = '\n  '

        for style in self.styles:
            styleElem = etree.Element('style')
            styleElem.text = style
            styleElem.tail = '\n  '
            root.append(styleElem)

        defs = etree.Element('defs')
        defs.text = '\n    '
        for use in self.uses:
            defs.extend(use)
        defs.tail = '\n  '
        root.append(defs)

        height = 0
        width = 0
        for image in self.images:
            for child in image.children:
                child.attrib['style'] = 'transform:translateX(%dpx)' % (width,)
            root.extend(image.children)
            image.children[-1].tail = '\n  '
            image.offset = width
            width += image.width
            if image.height > height:
                height = image.height
        image.children[-1].tail = '\n'

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

        # Write out the CSS!
        cssPath = os.path.join(output, self.name + 'Sprites.inc')
        print 'Writing:', cssPath
        css = open(cssPath, 'w')
        data = ''
        for image in self.images:
            data += (('%%define %s-image ' +
                     'list-style-image: url("chrome://browser/skin/%s.svg");' +
                     '-moz-image-region: rect(0px, %dpx, %dpx, %dpx);\n') %
                     (image.name, self.name, image.offset+image.width,
                      image.height, image.offset))
            data += (('%%define %s-hover ' +
                     '-moz-image-region: rect(%dpx, %dpx, %dpx, %dpx);\n') %
                     (image.name, image.height, image.offset+image.width,
                      image.height*2, image.offset))
            data += (('%%define %s-active ' +
                     '-moz-image-region: rect(%dpx, %dpx, %dpx, %dpx);\n') %
                     (image.name, image.height*2, image.offset+image.width,
                      image.height*3, image.offset))
            data += '\n'
        css.write(data)
        css.close()


class Variant(object):
    def __init__(self, variantDir, args):
        self.variantDir = variantDir
        self.baseDir = args.baseDir
        self.output = os.path.join(args.output, self.variantDir)

    def __str__(self):
        return 'Variant<' + self.variantDir + '>'

    def __repr__(self):
        return self.__str__()

    def getFile(self, filename):
        filePath = os.path.join(self.baseDir, self.variantDir, filename)
        if os.path.exists(filePath):
            return filePath
        return os.path.join(self.baseDir, filename)

    def getDefsFile(self, filename):
        filePath, xmlId = filename.split('#')
        filePath = self.getFile(filePath)
        print filePath, xmlId
        return (filePath, xmlId)

    def make(self, spritesheets):
        print
        print 'Making', self
        # Get images in spritesheet for variant…
        for spritesheet in spritesheets:
            sheet = spritesheet.getVariant(self)
            print '  ->', sheet, sheet.images, sheet.styles, sheet.uses
            sheet.write(self.output)


def getVariants(args):
    variants = os.walk(args.baseDir).next()[1]
    variants = [Variant(variant, args) for variant in variants]
    if len(variants) == 0:
        raise Usage('No subdirectory-based variants found in %s.' %
                    (blue(args.baseDir, bold=True),),
                    (args.baseDir,))
    return variants


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
        args = parser.parse_args(argv[1:])
        print args
        spritesheets = processManifest(args)
        print 'Spritesheets: ' + str(spritesheets)
        variants = getVariants(args)
        for variant in variants:
            variant.make(spritesheets)
    except Usage, err:
        print >>sys.stderr
        print >>sys.stderr, red('Error:', bold=True)
        print >>sys.stderr, err.msg
        print >>sys.stderr
        print >>sys.stderr, green('for help use --help', bold=True)
        return 2

if __name__ == '__main__':
    sys.exit(main())
