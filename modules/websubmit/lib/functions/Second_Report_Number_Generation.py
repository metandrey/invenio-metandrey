# -*- coding: utf-8 -*-

## This file is part of Invenio.
## Copyright (C) 2008, 2009, 2010, 2011 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""This function is based upon Report_Number_Generation.
   Whereas Report_Number_Generation is used to generate the FIRST report-number
   for a record, this function should be used to generate the SECOND report
   number, should one be required.
   A good example of its use may be when a document has been approved and is
   given another report number after approval.
   The generated report number will be saved into a file (name specified in one
   of the function's parameters) in the submission's working directory.
"""

__revision__ = "$Id$"

import cgi
import re
import os
import time
from invenio.config import CFG_SITE_SUPPORT_EMAIL
from invenio.websubmit_config import InvenioWebSubmitFunctionError
from invenio.errorlib import register_exception
from invenio.config import CFG_WEBSUBMIT_COUNTERSDIR


def Second_Report_Number_Generation(parameters, curdir, form, user_info=None):
    """
    This function's task is to generate a SECONDARY report number.
    Some document types require more than one report number.  The function
    "Report_Number_Generation" should be used to generate the PRIMARY
    report number (for various reasons, including the fact that that
    function populates the global "rn" with the document's main report
    number). This function then, should be used to generate the secondary
    report number.
    This function doesn't populate any global variable with the secondary
    report number, meaning that it should only be called if a secondary
    report number actually needs to be generated by the system (i.e. not
    if the user is to supply this secondary report number via the submission
    form.
    A use case for this function could be when a document is approved as
    an official note of some sort. Before approval for example, it could
    be classed as a Communication and have its own "Communication number".
    At approval time however, it could be given a new "official note"
    number, and this function could be used to generate the new number.
    So in short, the function behaves rather like Report_Number_Generation
    and was infact based upon that function. It:
          + Creates a "report number" according to some format and using some
            counter files.
          + Writes that new "report number" to a file in the submission's
            working directory.
            (** If the "second report number" file already exists in the
             submission's working directory, it merely exits silently.)

    Parameters:

    @param 2nd_counterpath: (string) - the path to the counter file that
        is used to create the report number.
        The counter path can make use of <PA></PA> in order to specify
        some value that should be included in the path:
          <PA>yy</PA> --> Include the year in the path
          <PA>categ</PA> --> Include the submission's category in the path.
          <PA>file[re]:name_of_file[regular expression to match]</PA> -->
              Include the first line of file (in curdir), matching [re]
          <PA>file*[re]:name_of_file [regular expression to match]</PA> -->
              Include all the lines of a file (in curdir), matching [re]
              separated by - (dash) char.

    @param 2nd_rn_file: (string) - the name of the file that is to be
        created containing the secondary report number. The file will be
        created in the submission's working directory.

    @param 2nd_rn_format: (string) - The format according to which the
        secondary report number will be created.

    @param 2nd_rncateg_file: (string) - the name of the file (in the
        submission's working directory) that contains the category of the
        document.
        The value in this file can be put into the report number by
        including <PA>categ</PA> anywhere that it is needed in the report-
        number format.

    @param 2nd_rn_yeargen: (string) - the instruction used for generating
        the year if one is to be used in the report number.
        The parameter should take either the value "AUTO" - in which case
        the year component of the report number will be a 4-digit
        representation for the current year - or - the name of a file in
        the submission's working directory that contains the year that should
        be included in the report number.
        Note, if the parameter contains the name of a file, it will be assumed
        that if the length of its contents is 10 chars, its value will be a
        date in the format "dd/mm/yyyy" and the last 4 characters will be
        taken as the year.  Otherwise if the length is not 10 characters, it
        will be assumed that the file simply contained a year and its
        contents will be taken as-is. If the file cannot be opened, an
        InvenioWebSubmitFunctionError exception will be raised. If no value
        is provided for this parameter, the year in the format YYYY will be
        used.
        The value that is finally created using this parameter for year will
        be used in the final report number anywhere that the format contains
        <PA>yy</PA>.
       Note:
       Tages that use <PA></PA> can take values as follows:
          <PA>yy</PA> --> Include the year (as determined by 2nd_rn_yeargen).
          <PA>categ</PA> --> Include the submission's category.
          <PA>file[re]:name_of_file[regular expression to match]</PA> -->
              Include the first line of file (in curdir), matching [re]
          <PA>file*[re]:name_of_file [regular expression to match]</PA> -->
              Include all the lines of a file (in curdir), matching [re]
              separated by - (dash) char.

    @param 2nd_nb_length: (string) the number of digits for the
        report number. Eg: '3' for XXX-YYYY-025 or '4' for
        XXX-YYYY-0025. If more are needed (all available digits have
        been used), the length is automatically extended. Choose 1 to
        never have leading zeros. Default length: 3.

    @return: (string) - empty string.

    @Exceptions raised: InvenioWebSubmitFunctionError - upon unexpected
        error.
    """
    ######################
    ## Internal function definition:
    ######################
    def get_pa_tag_content(pa_content):
        """Get content for <PA>XXX</PA>.
        @param pa_content: MatchObject for <PA>(.*)</PA>.
        return: if pa_content=yy => 4 digits year
                if pa_content=categ =>category
                if pa_content=file[re]:a_file => first line of file a_file matching re
                if pa_content=file*p[re]:a_file => all lines of file a_file, matching re,
                                              separated by - (dash) char.
        """
        pa_content=pa_content.groupdict()['content']
        sep = '-'
        out = ''
        if pa_content == 'yy':
            out = yy
        elif pa_content == 'categ':
            out = category
        elif pa_content.startswith('file'):
            filename = ""
            with_regexp = 0
            regexp = ""
            if "[" in pa_content:
                with_regexp = 1
                split_index_start = pa_content.find("[")
                split_index_stop =  pa_content.rfind("]")
                regexp = pa_content[split_index_start+1:split_index_stop]
                filename = pa_content[split_index_stop+2:]#]:
            else :
                filename = pa_content.split(":")[1]
            if os.path.exists(os.path.join(curdir, filename)):
                fp = open(os.path.join(curdir, filename), 'r')
                if pa_content[:5]=="file*":
                    out = sep.join(map(lambda x: re.split(regexp, x.strip())[-1], fp.readlines()))
                else:
                    out = re.split(regexp, fp.readline().strip())[-1]
                fp.close()
        return out
    ######################
    ## End of internal function definition:
    ######################
    document_type = form['doctype']
    access_number = form['access']

    ############
    ## Get parameter values and sanitize them:
    ############
    ############
    ## Report number length
    ############
    new_nb_length = 3
    if parameters.has_key('2nd_nb_length') and \
           parameters['2nd_nb_length'].isdigit():
        new_nb_length = int(parameters['2nd_nb_length'])
    ############
    ## Category file name - when category is included in the new report number
    ############
    try:
        new_rn_categ_filename = parameters['2nd_rncateg_file']
    except KeyError:
        new_rn_categ_filename = ""
    else:
        if new_rn_categ_filename is None:
            new_rn_categ_filename = ""
    ## Get the "basename" for the report-number file:
    new_rn_categ_filename = os.path.basename(new_rn_categ_filename).strip()
    if new_rn_categ_filename != ""  and \
           os.path.exists("%s/%s" % (curdir, new_rn_categ_filename)):
        try:
            fh_category = open("%s/%s" % (curdir, new_rn_categ_filename), "r")
            category = fh_category.read()
            fh_category.close()
        except IOError:
            register_exception()
        else:
            ## No newlines in category:
            category = category.replace("\n", "").replace("\r", "")
    else:
        category = ""
    ############
    ## Get the details of whether to automatically generate the year, or
    ## whether to get it from a file (if the report number uses a year.
    ############
    try:
        new_rn_yeargen = parameters['2nd_rn_yeargen']
    except IOError:
        new_rn_yeargen = ""
    else:
        if new_rn_yeargen is None:
            new_rn_yeargen = ""
    if new_rn_yeargen == "AUTO":
        ## If the function is configured to automatically generate the year,
        ## it should take the format "YYYY" (e.g. 2008). It should also be the
        ## current year:
        yy = time.strftime("%Y")
    elif new_rn_yeargen != "":
        ## Apparently, the value to be used for year should be taken from a
        ## file.
        new_rn_yeargen = os.path.basename(new_rn_yeargen).strip()
        if new_rn_yeargen != "" and \
           os.path.exists("%s/%s" % (curdir, new_rn_yeargen)):
            try:
                fh_year = open("%s/%s" % (curdir, new_rn_yeargen), "r")
                yy = fh_year.read()
                fh_year.close()
            except IOError:
                err_msg = "Error in Second_Report_Number_Generation: It " \
                          "wasn't possible to open the file containing " \
                          "the year: [%s]. Please report this problem to " \
                          "[%s]." % (cgi.escape(new_rn_yeargen), \
                                     cgi.escape(CFG_SITE_SUPPORT_EMAIL))
                register_exception(prefix=err_msg)
                raise InvenioWebSubmitFunctionError(err_msg)
            else:
                ## It is assumed that the contents of the date file will be
                ## either the year (in the format YYYY) or the date (in the
                ## format DD/MM/YYYY). If it is 10 chars in length, we take
                ## the last 4, assuming that they are the year component of
                ## the date. If not, we take the whole string, assuming that
                ## it is just the year anyway.
                yy = yy.strip()
                if len(yy) == 10:
                    yy = yy[-4:]
        elif new_rn_yeargen != "":
            ## Although a "valid" filename for the 2nd_rn_yeargen parameter had
            ## been provided, the file didn't exist.
            err_msg = "Error in Second_Report_Number_Generation: It " \
                      "wasn't possible to open the file containing " \
                      "the year: [%s]. Please report this problem to " \
                      "[%s]." % (cgi.escape(new_rn_yeargen), \
                                 cgi.escape(CFG_SITE_SUPPORT_EMAIL))
            raise InvenioWebSubmitFunctionError(err_msg)
        else:
            ## The filename provided for the 2nd_rn_yeargen parameter was
            ## invalid.
            err_msg = "Error in Second_Report_Number_Generation: The " \
                      "function has been configured with an invalid " \
                      "filename for the year (2nd_rn_yeargen). Please " \
                      "report this problem to [%s], quoting the document " \
                      "type [%s]." \
                      % (cgi.escape(CFG_SITE_SUPPORT_EMAIL), \
                         cgi.escape(document_type))
            raise InvenioWebSubmitFunctionError(err_msg)
    else:
        ## No value for the year-generation parameter. Just use the current
        ## year.
        yy = time.strftime("%Y")
    ############
    ## Counter Path:
    ############
    try:
        new_rn_counter_path = parameters['2nd_counterpath']
    except KeyError:
        new_rn_counter_path = ""
    else:
        if new_rn_counter_path is None:
            new_rn_counter_path = ""
    counter_path = re.sub('<PA>(?P<content>[^<]*)</PA>',
                          get_pa_tag_content,
                          new_rn_counter_path)
    counter_path = counter_path.replace(" ", "").replace("\n", "")
    ## Counter path isn't allowed to contain "../" (no moving below the
    ## counters directory) and must not be empty. If either of these cases
    ## is true, it is considered to be an error:
    if counter_path == "" or counter_path.find("../") != -1:
        ## Invalid counter path.
        err_msg = "Error in Second_Report_Number_Generation: The function " \
                  "has been configured with an invalid value for " \
                  "2nd_counterpath. Please report this problem to " \
                  "[%s]." % cgi.escape(CFG_SITE_SUPPORT_EMAIL)
        raise InvenioWebSubmitFunctionError(err_msg)
    ############
    ## New Report Number's File Name:
    ############
    try:
        new_rn_filename = parameters['2nd_rn_file']
    except KeyError:
        new_rn_filename = ""
    else:
        if new_rn_filename is None:
            new_rn_filename = ""
    ## Get the "basename" for the report-number file:
    new_rn_filename = os.path.basename(new_rn_filename).strip()
    if new_rn_filename == "":
        ## No file name provided for the new report-number. This is
        ## considered to be an error.
        err_msg = "Error in Second_Report_Number_Generation: The function " \
                  "has been configured with an invalid value for " \
                  "2nd_rn_file. Please report this problem to " \
                  "[%s]." % cgi.escape(CFG_SITE_SUPPORT_EMAIL)
        raise InvenioWebSubmitFunctionError(err_msg)
    ############
    ## Report Number Format:
    ############
    try:
        new_rn_format = parameters['2nd_rn_format']
    except KeyError:
        new_rn_format = ""
    else:
        if new_rn_format is None:
            new_rn_format = ""
    new_rn_format = re.sub('<PA>(?P<content>[^<]*)</PA>',
                           get_pa_tag_content,
                           new_rn_format)
    ############
    ## End of treatment of parameters.
    ############
    ############
    ## Test to see whether the second report number file already exists:
    if not os.path.exists("%s/%s" % (curdir, new_rn_filename)):
        ## The new report number file doesn't exist. Create it.
        new_rn = Create_Reference(counter_path, new_rn_format, new_nb_length)
        new_rn = re.compile('\s').sub('', new_rn)
        ## Write it to file:
        # The file edsrn is created in the submission directory, and it stores the report number
        try:
            fh_new_rn_file = open("%s/%s" % (curdir, new_rn_filename), "w")
            fh_new_rn_file.write(new_rn)
            fh_new_rn_file.flush()
            fh_new_rn_file.close()
        except IOError:
            ## Unable to create the new report-number's file.
            err_msg = "Error in Second_Report_Number_Generation: It " \
                      "wasn't possible to write out the newly generated " \
                      "'second' report number (%s) to the file [%s]. " \
                      "Please report this problem to [%s], quoting the " \
                      "document type [%s], the submission access number " \
                      "[%s] and the new report number [%s]."
            register_exception(prefix=err_msg % (new_rn, \
                                                 new_rn_filename, \
                                                 CFG_SITE_SUPPORT_EMAIL, \
                                                 document_type, \
                                                 access_number, \
                                                 new_rn))
            raise InvenioWebSubmitFunctionError(err_msg % \
                                  (cgi.escape(new_rn), \
                                   cgi.escape(new_rn_filename), \
                                   cgi.escape(CFG_SITE_SUPPORT_EMAIL), \
                                   cgi.escape(document_type), \
                                   cgi.escape(access_number), \
                                   cgi.escape(new_rn)))
    return ""


## Create_Reference function below actually creates the reference number:

def Create_Reference(counter_path, ref_format, nb_length=3):
    """From the counter-file for this document submission, get the next
       reference number and create the reference.
    """
    ## Does the WebSubmit CFG_WEBSUBMIT_COUNTERSDIR directory exist? Create it if not.
    if not os.path.exists(CFG_WEBSUBMIT_COUNTERSDIR):
        ## counters dir doesn't exist. Create:
        try:
            os.mkdir(CFG_WEBSUBMIT_COUNTERSDIR)
        except:
            ## Unable to create the CFG_WEBSUBMIT_COUNTERSDIR Dir.
            msg = "File System: Cannot create counters directory %s" % CFG_WEBSUBMIT_COUNTERSDIR
            raise InvenioWebSubmitFunctionError(msg)

    ## Now, take the "counter_path", and split it into the head (the path
    ## to the counter file) and tail (the name of the counter file itself).
    (head_cpath, tail_cpath) = os.path.split(counter_path)
    if head_cpath.strip() != "":
        ## There is a "head" for counter-path. If these directories
        ## don't exist, make them:
        if not os.path.exists("%s/%s" % (CFG_WEBSUBMIT_COUNTERSDIR, head_cpath)):
            try:
                os.makedirs(os.path.normpath("%s/%s" % (CFG_WEBSUBMIT_COUNTERSDIR, head_cpath)))
            except OSError:
                msg = "File System: no permission to create counters " \
                      "directory [%s/%s]" % (CFG_WEBSUBMIT_COUNTERSDIR, head_cpath)
                raise InvenioWebSubmitFunctionError(msg)

    ## Now, if the counter-file itself doesn't exist, create it:
    if not os.path.exists("%s/%s" % (CFG_WEBSUBMIT_COUNTERSDIR, counter_path)):
        try:
            fp = open("%s/%s" % (CFG_WEBSUBMIT_COUNTERSDIR, counter_path),"w")
        except:
            msg = "File System: no permission to write in counters " \
                  "directory %s" % CFG_WEBSUBMIT_COUNTERSDIR
            raise InvenioWebSubmitFunctionError(msg)
        else:
            fp.write("0")
            fp.close()
    ## retrieve current counter value
    try:
        fp = open("%s/%s" % (CFG_WEBSUBMIT_COUNTERSDIR, counter_path), "r")
    except IOError:
        ## Unable to open the counter file for reading:
        msg = "File System: Unable to read from counter-file [%s/%s]." \
              % (CFG_WEBSUBMIT_COUNTERSDIR, counter_path)
        raise InvenioWebSubmitFunctionError(msg)
    else:
        id = fp.read()
        fp.close()

    if id == "":
        ## The counter file seems to have been empty. Set the value to 0:
        id = 0

    ## increment the counter by 1:
    id = int(id) + 1

    ## store the new value in the counter file:
    try:
        fp = open("%s/%s" % (CFG_WEBSUBMIT_COUNTERSDIR, counter_path), "w")
    except IOError:
        ## Unable to open the counter file for writing:
        msg = "File System: Unable to write to counter-file [%s/%s]. " \
              % (CFG_WEBSUBMIT_COUNTERSDIR, counter_path)
        raise InvenioWebSubmitFunctionError(msg)
    else:
        fp.write(str(id))
        fp.close()
    ## create final value
    reference = ("%s-%0" + str(nb_length) + "d") % (ref_format, id)
    ## Return the report number prelude with the id concatenated on at the end
    return reference
