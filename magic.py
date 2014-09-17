#! /usr/bin/env python

import argparse
from clint.textui.colored import red, green, blue

from time import sleep
from clint.textui import progress
import csv
import os
import sys


class Usage(Exception):
    def __init__(self, msg, data):
        self.msg = msg
        self.data = data


def processManifest(args):
    # print "Hello World!"
    # print args
    manifestPath = os.path.join(args.baseDir, 'sprites.mf')
    if not os.path.exists(manifestPath):
        raise Usage("Manifest not found at %s." %
                    (red(manifestPath, bold=True)),
                    (manifestPath,))
    lineCount = len(open(manifestPath).readlines())

    manifest = csv.DictReader(open(manifestPath), skipinitialspace=True)
    manifest.fieldnames = ['filename', 'spritesheet']
    spritesheets = {}

    for line in progress.bar(manifest,
                             label="Reading Manifest: ",
                             expected_size=lineCount):
        sheet = line['spritesheet']
        image = line['filename']
        imagePath = os.path.join(args.baseDir, image)
        if not os.path.exists(imagePath):
            raise Usage("Image not found at %s from %s, %s." %
                        (red(imagePath, bold=True),
                         blue(manifestPath, bold=True),
                         blue('line ' + str(manifest.line_num), bold=True)),
                        (imagePath, manifestPath, manifest.line_num))
        spritesheets.setdefault(sheet, []).append(image)
    return spritesheets


def getVariants(args):
    variants = os.walk(args.baseDir).next()[1]
    if len(variants) == 0:
        raise Usage("No subdirectory-based variants found in %s." %
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
            action="store",
            help='The directory to find the images and the manifests in.')
        parser.add_argument(
            '-o', '--output',
            default='output',
            help='The directory to store the output in.')
        args = parser.parse_args(argv[1:])
        spritesheets = processManifest(args)
        print "Spritesheets: " + str(spritesheets)
        variants = getVariants(args)
        for variant in variants:
            print "Making " + variant
            # Get images in spritesheet for variant…
    except Usage, err:
        print >>sys.stderr
        print >>sys.stderr, red("Error:", bold=True)
        print >>sys.stderr, err.msg
        print >>sys.stderr
        print >>sys.stderr, green("for help use --help", bold=True)
        return 2

if __name__ == "__main__":
    sys.exit(main())
