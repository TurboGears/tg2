""" TurboGears offline docs fetcher

TODO:

  * replace links to proper link

"""
import urllib2
import re
import os

# links
acquire_site = "http://docs.turbogears.org/"
doclist = "TitleIndex?action=titleindex"

# pattern
comment = "PageCommentData"

# retrive_docs
raw = "?action=raw"
ext = ".rst"

brokenlink = []

def get_doclist(version):
    docs  = urllib2.urlopen(acquire_site + doclist)
    targets = []
    for link in docs.readlines(): 
        if re.match(version, link) and (not re.match(comment, link)):
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

def proc_doc(link, doc, targets, version):
    """
    process doc, and save the doc to proper destination    
    """
    #from docutils.core import publish_parts
    #outbin = publish_parts(doc.read(),writer_name="html")["html_body"]

    #prepare_dest()
    link = link.strip()
    if link == version:
        link = version+"/index"

    # file path
    place = os.getcwd()
    filepath = place+"/"+link+ext
    filepath.replace('\\', '/') 

    # silly proc
    doc = doc.read()

    #replace '<2.0/' to '<'
    doc = doc.replace("<"+version+"/", "<")

    #get rid of comments
    doc = re.sub(r"\.\. macro:: .*\]\]", "", doc) # macro
    doc = re.sub(r"## page.*", "", doc) # ## page
    doc = re.sub(r"#format .*", "", doc) # format

    # replace links to proper link
    """for urllink in targets:
        if urllink == version:
            #urllink="1.0/index.html"
            pass
        else:
            doc = doc.replace(urllink, urllink+ext)"""

    save_doc(filepath, doc)

def process_docs(targets, version):
    # get css and pic

    # retrive docs
    for link in targets:
        doc = retrive_docs(link, "rst")
        if doc is not None:
            proc_doc(link, doc, targets, version)

    print "done, brokenlink=%s"%brokenlink

    # make the tarball


if __name__ == '__main__':
    acquire_version = "2.0"
    targets = get_doclist(version = acquire_version)
    process_docs(targets, version = acquire_version)
