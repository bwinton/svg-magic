#! /usr/bin/env python
# coding=utf-8

import argparse
from clint.textui.colored import red, green, blue

from time import sleep
from clint.textui import progress
import csv
import os
import sys
from lxml import etree


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
        spritesheets.setdefault(sheet, []).append(image)
    return spritesheets


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
        self.sheets = []
        pi = self.tree.getroot().getprevious()
        if (isinstance(pi, etree._ProcessingInstruction) and
                pi.target == 'xml-stylesheet' and
                pi.attrib['type'] == 'text/css'):
            self.sheets.append(pi.attrib['href'])
        self.uses = self.tree.findall('{http://www.w3.org/2000/svg}use')
        self.uses = [use.attrib['{http://www.w3.org/1999/xlink}href']
                     for use in self.uses]
        # import pdb;pdb.set_trace()


class Variant(object):
    def __init__(self, variantDir, args):
        self.variantDir = variantDir
        self.baseDir = args.baseDir

    def __str__(self):
        return 'Variant<' + self.variantDir + '>'

    def __repr__(self):
        return self.__str__()

    def getFile(self, filename):
        filePath = os.path.join(self.baseDir, self.variantDir, filename)
        if os.path.exists(filePath):
            return filePath
        return os.path.join(self.baseDir, filename)

    def make(self, spritesheets):
        print
        print 'Making', self
        # Get images in spritesheet for variant…
        for spritesheet in spritesheets:
            images = spritesheets[spritesheet]
            print '  ->', spritesheet, images
            images = [Image(self.getFile(image)) for image in images]
            sheets = set()
            uses = set()
            for image in images:
                sheets.update(image.sheets)
                uses.update(image.uses)
                print image.name, image.sheets, image.uses
            sheets = [self.getFile(sheet) for sheet in sorted(sheets)]
            uses = sorted(uses)
            print sheets, uses


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
