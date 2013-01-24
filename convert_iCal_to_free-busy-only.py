#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-01-24 22:36:00 vk>


## TODO:
## * fix parts marked with «FIXXME»

DEFAULT_SUMMARY = 'busy'

## this list is case sensitive:
CATEGORIES = [
    ["@Stadt", "in der Stadt"], 
    ["lp", "nicht so wichtig"], 
    ["@TUG", "an der TU Graz"],
    ["@ALW", "daheim"],
    ["@out_of_town", "nicht in Graz"],
#    ["", ""],
#    ["", ""],
#    ["", ""],
#    ["", ""],
    ]

## ===================================================================== ##
##  You might not want to modify anything below this line if you do not  ##
##  know, what you are doing :-)                                         ##
## ===================================================================== ##

## NOTE: in case of issues, check iCalendar files using: http://icalvalid.cloudapp.net/

import os
import sys
import re
import time
import logging
from optparse import OptionParser


PROG_VERSION_NUMBER = u"0.1"
PROG_VERSION_DATE = u"2013-01-24"
INVOCATION_TIME = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())



USAGE = u"\n\
    " + sys.argv[0] + u" -i <inputfile.ics> -o <outputfile.ics>\n\
\n\
This script filters an iCalendar file. General entries like date, time,\n\
and header information is kept unchanged. Descriptions, categories, and\n\
summary gets replaced with a minimum of information.\n\
\n\
Please refer to README.org for further details.\n\
\n\
\n\
\n\
:copyright: (c) 2013 by Karl Voit <tools@Karl-Voit.at>\n\
:license: GPL v3 or any later version\n\
:bugreports: <tools@Karl-Voit.at>\n\
:version: "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE+"\n"

parser = OptionParser(usage=USAGE)

parser.add_option("-i", "--input", dest="inputfilename",
                  help="(path and) name of the iCalendar file to parse", metavar="FILE")

parser.add_option("-o", "--output", dest="outputfilename",
                  help="(path and) name of the iCalendar file where the result is written to", metavar="FILE")

parser.add_option("--dryrun", dest="dryrun", action="store_true",
                  help="Does not make any changes to the file system. Useful for testing behavior.")

parser.add_option("-O", "--overwrite", dest="overwrite", action="store_true",
                  help="Overwrite the output file without asking, if the output file exists.")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

parser.add_option("--version", dest="version", action="store_true",
                  help="display version and exit")

(options, args) = parser.parse_args()


def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def error_exit(errorcode, text):
    """exits with return value of errorcode and prints to stderr"""

    sys.stdout.flush()
    logging.error(text)

    sys.exit(errorcode)


def add_to_field(field, string):
    """add string to field line"""

    if field:
        ## add an additional string
        newfield = field + '\; ' + string
    else:
        ## add first string
        newfield = string

    return newfield


def parse_for_known_tags(categories):
    """parse summary and categories for pre-defined tags and 
    generate new summary and location accordingly"""

    newsummary = newlocation = ""

    catlist = categories[11:].split(',')
    #logging.debug("catlist [%s]" % str(catlist) )

    if catlist:
        ## FIXXME: this algorithm is not optimized for performance! (not necessary for few items)
        for tag in catlist:
            #logging.debug("tag [%s]" % tag )
            for search, replacement in CATEGORIES:
                #logging.debug("search: [%s]  replacement: [%s]" % (search, replacement) )

                if tag == search:
                    ## we have a match; insert replacement string into summary

                    logging.debug("found known tag [%s], replacing with [%s]" % (search, replacement))
                    newsummary = add_to_field(newsummary, replacement)
                    
                    ## if the tag starts with an at-sign, add it to location as well:
                    if tag.startswith('@'):

                        logging.debug("found location tag [%s]; adding [%s] to location field" % (search, replacement))
                        newlocation = add_to_field(newlocation, replacement)

            else:
                ## tag does NOT match; look out for generic location tag:

                ## if the tag starts with an at-sign, add it to location as well:
                if tag.startswith('@'):

                    logging.debug("found generic location tag [%s]" % (tag))
                    newlocation = add_to_field(newlocation, tag[1:])
                        
    return newsummary, newlocation


def handle_file(inputfilename, outputfilename, dryrun):
    """handles inputfile and generates outputfile"""

    logging.debug( "--------------------------------------------")
    logging.info(sys.argv[0] + "   ... called with ... ")
    logging.info("input file \""+ inputfilename + "\"  ... and ...")
    logging.info("output file \""+ outputfilename + "\"")

    parsing_header = True
    newentry = ""
    currentsummary = ""
    currentdescription = ""
    currentcategories = ""
    currentlocation = ""

    with open(outputfilename, 'w') as output:

        input = open(inputfilename, 'r')
        for rawline in input:
        
            newline = ""
            line = rawline.strip()
            logging.debug("line: %s" % line)
            
            ## detect new event (and header end)
            if line.startswith('BEGIN:VEVENT'):
                logging.debug("new VEVENT .............................................")
                newline = line
        
                ## header is finished:
                if parsing_header and not dryrun:
                    output.write(newentry)
                    newentry = ""
        
                parsing_header = False
                
            ## lines that will be copied to output (unmodified):
            elif line.startswith('UID:') or \
                    line.startswith('DTSTART') or \
                    line.startswith('DTEND'):
                newline = line
        
            ## temporarily store content fields:
            elif line.startswith('SUMMARY:'):
                currentsummary = line
            elif line.startswith('DESCRIPTION:'):
                currentdescription = line
            elif line.startswith('CATEGORIES:'):
                currentcategories = line
        
            ## write completed event entry:
            elif line.startswith('END:VEVENT'):
        
                ## entry is finished
                if newentry and not dryrun:
        
                    ## parse categories for known substrings
                    ## copy known substrings to description line
                    ## copy known location-based substrings to location line
                    currentsummaryline, currentlocationline = parse_for_known_tags(currentcategories)
        
                    output.write(newentry)  ## entry so far without description, location, or end
        
                    ## write description:
                    if currentsummaryline:
                        output.write('SUMMARY: ' + DEFAULT_SUMMARY + '\; ' + currentsummaryline + '\n')
                    else:
                        output.write('SUMMARY: ' + DEFAULT_SUMMARY + '\n')
        
                    ## if found, write location:
                    if currentlocationline:
                        output.write('LOCATION: ' + currentlocationline + '\n')
        
                    ## write end of iCalendar entry
                    output.write(line + '\n')
        
                    ## reset entries:
                    currentsummary = ""
                    currentdescription = ""
                    currentcategories = ""
                    currentlocation = ""
                    newentry = ""
        
            elif line.startswith('END:VCALENDAR'):
                    output.write(line + '\n')
        
            if parsing_header:
                newline = line
        
            if newline and not dryrun:
                #output.write(newline + '\n')
                newentry += newline + '\n'
        
    

def main():
    """Main function"""

    if options.version:
        print os.path.basename(sys.argv[0]) + " version "+PROG_VERSION_NUMBER+" from "+PROG_VERSION_DATE
        sys.exit(0)

    handle_logging()
    dryrun = False

    if options.dryrun:
        logging.info("Option \"--dryrun\" found, running a simulation, not modifying anything on file system.")
        dryrun = True

    if not options.inputfilename and not options.outputfilename:
        error_exit(1,"Please give me an input file to parse \"--input\" and an output file to generate \"--output\".")

    if not options.inputfilename and options.outputfilename:
        error_exit(2,"Please give me an input file to parse \"--input\".")

    if options.inputfilename and not options.outputfilename:
        error_exit(3,"Please give me an output file to generate \"--output\".")

    logging.debug("dryrun: " + str(dryrun))

    ## make sure that outputfilename does not exist or handle situation:
    ## FIXXME: handle situation when outputfilename is a folder (and not a file)
    if os.path.exists(options.outputfilename):
       if options.overwrite:
           logging.debug("deleting old output file because of overwrite parameter")
           if not dryrun:
               os.remove(options.outputfilename)
           else:
               logging.debug("dryrun: I would delete the file \"%s\" now." % options.outputfilename)
       else:
           error_exit(4, "Sorry, output file \"%s\" already exists and you did not use the overwrite option \"--overwrite\"." % options.outputfilename)
           
    handle_file(options.inputfilename, options.outputfilename, dryrun)

    logging.info("successfully finished.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################
          
#end
