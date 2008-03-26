""" TurboGears offline docs generator

TODO:
  
  * replace links to proper link
  * make the tarball
  * make the PDF
 
Fixed:
  * create folders automatically
  * get css and pic

"""
import urllib2
import re
import os

# links
acquire_site = "http://docs.turbogears.org/"
doclist = "TitleIndex?action=titleindex"

# pattern
acquire_version = "2.0"
comment = "PageCommentData"
#"<2.0/"
verp = "<"+acquire_version+"/"
verr = "<"

# retrive_docs
raw = "?action=raw"
ext = ".rst"

brokenlink = []

def get_doclist(acquire_version):
    docs  = urllib2.urlopen(acquire_site + doclist)
    targets = []
    for link in docs.readlines(): 
        if re.match(acquire_version, link) and (not re.match(comment, link)):
            targets.append(link)
    return targets
        
def retrive_docs(link, format):
    """
    get the doc with proper format
    
    @param link: the link
    @type link: string
    @param format: html or rst
    @type format: string
    @return: doc
    @rtype: file descriptor
    """
    link = link.strip()
    
    if format == "html":
        print "download " + acquire_site + link
        try:
            doc  = urllib2.urlopen(acquire_site + link)
        except:
            brokenlink.append(link)
            return None
        
    if format == "rst":
        print "download " + acquire_site + link + raw
        try:
            doc  = urllib2.urlopen(acquire_site + link + raw)
        except:
            brokenlink.append(link)
            return None

    return doc

def save_doc(filepath, doc):
    # split package and basename
    divider = filepath.rfind("/")
    if divider > -1:
        package = filepath[0:divider]
        basename = filepath[divider+1:]

    # caught exception
    if (not os.access(".", os.W_OK)):
        pass

    # create directory
    if not os.path.exists(package):
        try:
            os.mkdir(package)
        except OSError, e:
            print e
            return

    # save file to destination    
    print "saved to " + filepath
    open(filepath,'w').write(doc)

def proc_doc(link, doc, targets):
    """
    process doc, and save the doc to proper destination    
    """
    #from docutils.core import publish_parts
    #outbin = publish_parts(doc.read(),writer_name="html")["html_body"]

    #prepare_dest()
    link = link.strip()
    if link == acquire_version:
        link = acquire_version+"/index"

    # file path
    place = os.getcwd()
    filepath = place+"/"+link+ext
    filepath.replace('\\', '/') 

    # silly proc
    doc = doc.read()

    #replace '<2.0/' to '<'
    doc = doc.replace(verp, verr)

    # replace links to proper link
    """for urllink in targets:
        if urllink == acquire_version:
            #urllink="1.0/index.html"
            pass
        else:
            doc = doc.replace(urllink, urllink+ext)"""

    save_doc(filepath, doc)

def process_docs(targets):
    # get css and pic

    # retrive docs
    for link in targets:
        doc = retrive_docs(link, "rst")
        if doc is not None:
            proc_doc(link, doc, targets)

    print "done, brokenlink=%s"%brokenlink

    # make the tarball


if __name__ == '__main__':

    targets = get_doclist(acquire_version = "2.0")
    process_docs(targets)
