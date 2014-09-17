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


SPRITESHEET_SVG = io.BytesIO("""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
                     "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">

<svg version="1.1"
     xmlns="http://www.w3.org/2000/svg"
     x="0"
     y="0">
</svg>""")


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
    def __init__(self, image):
        self.name = image
        self.tree = etree.parse(self.name)
        self.parseTree()

    def __str__(self):
        return 'Image<' + self.name + '>'

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
        self.width = attrib['width']
        self.height = attrib['height']


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

    def getVariant(self, variant):
        new = Spritesheet(self.name, self.images[:])
        new.images = [Image(variant.getFile(image)) for image in new.images]
        styles = set()
        uses = set()
        for image in new.images:
            styles.update(image.styles)
            uses.update(image.uses)
            print image.name, image.width, image.height
        styles = [variant.getFile(sheet) for sheet in sorted(styles)]
        uses = [variant.getDefsFile(use) for use in sorted(uses)]
        new.styles = styles
        new.uses = uses
        return new

    def write(self, output):
        tree = etree.parse(SPRITESHEET_SVG)
        root = tree.getroot()
        root.attrib['width'] = '16'
        root.attrib['height'] = '16'
        root.attrib['viewbox'] = '0 0 16 16'

        for style in self.styles:
            style = etree.Element('style')
            style.tail = '\n'
            root.append(style)

        for use in self.uses:
            defs = etree.Element('defs')
            defs.tail = '\n'
            root.append(defs)

        for image in self.images:
            g = etree.Element('image')
            g.text = str(image)
            g.tail = '\n'
            root.append(g)

        data = etree.tostring(tree,
                              xml_declaration=True,
                              encoding='utf-8')
        print data

        if not os.path.exists(output):
            os.makedirs(output)
        svgPath = os.path.join(output, self.name + '.svg')
        print 'Writing:', svgPath
        svg = open(svgPath, 'w')
        svg.write(data)
        svg.close()


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
