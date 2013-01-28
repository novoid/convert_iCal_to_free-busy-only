#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2013-01-28 11:24:09 vk>


## TODO:
## * fix parts marked with «FIXXME»

DEFAULT_SUMMARY = 'busy'              ## in case no special tag is found

## this list is case sensitive:
CATEGORIES = [
    ["@Stadt", "in der Stadt"], 
    ["lp", "kann ich einfach absagen/auslassen"], 
    ["@TUG", "an der TU"],
    ["@ALW", "bin daheim"],
    ["@out_of_town", "nicht in Graz"],
    ["other", "andere Person - nicht von mir!"],
#    ["", ""],
#    ["", ""],
#    ["", ""],
    ]

## this list is case sensitive:
SUMMARY = [
    ["DND", "Handy auf leise"],  ## I mark events where my phone is silenced with "DND"
    [" ? ", "noch nicht fix!"],  ## events starting with " ? " are not fixed and might not happen at all
#    ["", ""],
#    ["", ""],
#    ["", ""],
    ]

## shows the original description line
SHOW_DESCRIPTION_TAG = 'public'

## overrules enything else and shows only DEFAULT_SUMMARY and no location
PRIVATE_TAG = 'private'

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


def parse_summary_for_known_tags(currentsummary, newsummary, newlocation):
    """parse summary for pre-defined strings in SUMMARY and generate
    new summary and location accordingly."""

    for entry in SUMMARY:
        if entry[0] in currentsummary:
            newsummary = add_to_field(newsummary, entry[1])
            logging.debug("summary searchstring [%s] found and added [%s] to newsummary" % ( entry[0], entry[1]))

    return newsummary, newlocation


def parse_categories_for_known_tags(summary, categories, newsummary, newlocation):
    """parse categories for pre-defined tags in CATEGORIES and generate new summary
    and location accordingly."""

    catlist = categories[11:].split(',')
    #logging.debug("catlist [%s]" % str(catlist) )

    if catlist:

        ## FIXXME: this algorithm is not optimized for performance! (not necessary for few items)
        for tag in catlist:
            #logging.debug("tag [%s]" % tag )

            if SHOW_DESCRIPTION_TAG == tag:
                newsummary = summary[9:] + '; ' + newsummary

            if PRIVATE_TAG == tag:
                ## overrule everything else
                return DEFAULT_SUMMARY, ""

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
    count_events = 0
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
                count_events+=1
                newline = line
        
                ## header is finished:
                if parsing_header and not dryrun:
                    output.write(newentry)
                    newentry = ""
        
                parsing_header = False
                
            ## lines that are identical in output:
            elif line.startswith('UID:') or \
                    line.startswith('DTSTART') or \
                    line.startswith('DTEND'):
                newline = line
        
            ## store content fields:
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

                    newsummary = newlocation = ""

                    ## parse summary for known substrings
                    newsummary, newlocation = \
                        parse_summary_for_known_tags(currentsummary, newsummary, newlocation)

                    logging.debug("newsummary: [%s]" % newsummary)
                    logging.debug("newlocation: [%s]" % newlocation)
        
                    ## parse categories for known substrings
                    newsummary, newlocation = \
                        parse_categories_for_known_tags(currentsummary, currentcategories, newsummary, newlocation)

                    logging.debug("newsummary: [%s]" % newsummary)
                    logging.debug("newlocation: [%s]" % newlocation)
        
                    output.write(newentry)  ## entry so far without description, location, or end
        
                    ## write description:
                    if newsummary:
                        output.write('SUMMARY: ' + newsummary + '\n')
                    else:
                        output.write('SUMMARY: ' + DEFAULT_SUMMARY + '\n')
        
                    ## if found, write location:
                    if newlocation:
                        output.write('LOCATION: ' + newlocation + '\n')
        
                    ## write end of iCalendar entry
                    output.write(line + '\n')
        
                    ## reset entries:
                    currentsummary = ""
                    currentdescription = ""
                    currentcategories = ""
                    currentlocation = ""
                    newentry = ""
                    not_sure = False
        
            elif line.startswith('END:VCALENDAR'):
                    output.write(line + '\n')
        
            if parsing_header:
                newline = line
        
            if newline and not dryrun:
                #output.write(newline + '\n')
                newentry += newline + '\n'

        return count_events
    


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
           
    count_events = handle_file(options.inputfilename, options.outputfilename, dryrun)

    logging.info("successfully finished converting %s events." % count_events)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################
          
#end
