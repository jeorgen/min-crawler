#!/usr/bin/python
# Based on the crawler described at: http://www.ibm.com/developerworks/linux/library/l-spider/

import urllib
import urlparse
import sys
import re
from cgi import escape
import time
import httpstatuscodes
import copy


from HTMLParser import HTMLParser

class Timer:
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start

class miniHTMLParser( HTMLParser ):

    viewedQueue = {}
    instQueue = []
    instQueueDict = {}
    badlinks = {}
    site = ''
    current_url = ''
    fo = None
    print_to_console = True
    
    def log(self,message):
        self.fo.write(message + '\n')
        if self.print_to_console:
            print message
            
    def on_leave_page(self):
            if not self.found_canonical:
                self.log("NO canonical link found for %s" % self.current_url)
            else:
                self.log("canonical link found for %s with value %s" % (self.current_url, self.found_canonical))

   
    def on_enter_page(self):
            self.found_canonical = None
        
        
    def get_next_link( self ):
        if self.instQueue == []:
            return ''
        else:
            return self.instQueue.pop(0)

    #def check_if_link_is dead(self):
        #pass
        
        
        
    def gethtmlfile( self ):
        #self.log( self.current_url)
        try:
            connection = urllib.urlopen(self.current_url)
        except IOError:
            print self.current_url
            raise
        if connection.code is not 200:
            self.log( "%s is NOT working, it returns connection code %d" % (self.current_url, connection.code))
            self.markbadlink(connection.code)
            return None
        if not self.current_url.startswith(self.site):
            return None # Not on this site so no further parsing, just checked for upness
        #import pdb;pdb.set_trace()
        if connection.headers.get('content-type').startswith('text/html'):
            encoding = connection.headers.getparam('charset')
            page = connection.read()
            if encoding:
                page = page.decode(encoding)        
            return page
        else:
            return None


    def handle_starttag( self, tag, attrs ):
        found_canonical = False
        if tag == 'link': # Check if we have the canonical tag and see what it is
            href = ""
            for attr, value in attrs:
                if attr == 'rel':
                    if value == 'canonical':
                        found_canonical = True
                elif attr == 'href':
                    #print "found href with value %s" % value
                    href = value
            if found_canonical:
                self.found_canonical = href
                    
        elif tag == 'a':
            for attr, value in attrs:
                if attr == u'href':
                    #self.log( "value for href is: " + value)
                    # remove site part
                    if value.startswith(u'mailto:') or value.startswith(u'javascript:'):
                        #self.log( "ignoring %s, mailto link" % value)
                        return
                    if value.startswith(self.site):
                        value = value[len(self.site):]
                        #self.log( "value is now %s, after removing %s" % (value, self.site))
                    # Below commented out since we want to check on external links upness too 
                    #if value.startswith(u'http://'):
                        #self.log( "ignoring %s, out of range" % value)
                    #    return
                    #if not value.startswith('/'):
                        #self.log( "WARNING relative link %s, on page %s" % (value,self.current_url ))
                    url = urlparse.urljoin(self.current_url, escape(value))
                    url, frag = urlparse.urldefrag(url)
                    #self.log( "canonical url is %s" % url)
                    self.addtoqueue(url)

                    
            #import pdb;pdb.set_trace()

    def markbadlink(self, code):
        message = "is not OK, returns status code %d" % code
        #if not self.viewedQueue.has_key(self.current_url):
            #self.viewedQueue[self.current_url] = [message,]
        #else:
            #self.viewedQueue[self.current_url].append(message)
        if not self.badlinks.has_key(code):
            self.badlinks[code] = [self.current_url,]
        else:
            self.badlinks[code].append(self.current_url)

    def addtoqueue(self, newstr):
        if not self.viewedQueue.has_key(newstr):
            self.viewedQueue[newstr] = {}
            self.instQueue.append( newstr )
        #else:
            #print "%s has been seen before" % newstr
        self.viewedQueue[newstr][self.current_url] = 1


def main():
    #import pdb;pdb.set_trace()
    if sys.argv[1] == '':
        self.log( "usage is ./minispider.py site")
        sys.exit(2)

    mySpider = miniHTMLParser()
    mySpider.site = sys.argv[1]

    mySpider.addtoqueue(mySpider.site)
    #mySpider.current_url = mySpider.site
    filename = time.strftime('%Y-%m-%d-%H-%M-%S')
    fo = open(filename, 'a')
    mySpider.fo = fo
    
    while mySpider.instQueue:
        mySpider.current_url = mySpider.get_next_link()
        mySpider.on_enter_page()
        #mySpider.log( "\nChecking link %s" % mySpider.current_url)
        #links_in_queue = len(mySpider.instQueue)
        #unique_links_in_queue = len(dict(zip(mySpider.instQueue,mySpider.instQueue)))
        #total_links_found = len(mySpider.viewedQueue.keys())
        #mySpider.log( "\nlinks in queue: %d" % links_in_queue)
        #mySpider.log( "\nunique links in queue: %d" % unique_links_in_queue)
        #mySpider.log( "\nTotal links found: %d" % total_links_found)
        #mySpider.log( "\nTotal pages visited: %d" % (total_links_found - links_in_queue))

        # Get the file from the site and link
        retfile = mySpider.gethtmlfile()
        if retfile is None:
            continue

        # Feed the file into the HTML parser
        try:
            mySpider.feed(retfile)
        except HTMLParser.HTMLParseError:
            mySpider.log ("could not parse %s" % mySpider.current_url)
        # Search the retfile here
        time.sleep(1)
        # Get the next link in level traversal order
        mySpider.on_leave_page()

    mySpider.close()

    mySpider.log( "\ndone\n")
    mySpider.log ("Links that did not work at least once while spidering. Plese check these")
    for statuscode in mySpider.badlinks.keys():
        mySpider.log ("\nstatus code %d %s" % (statuscode,httpstatuscodes.forhumans[statuscode]))
        badlinkshere = mySpider.badlinks[statuscode]
        for badlink in badlinkshere:
            mySpider.log ("\nLink %s is mentioned in these pages:" % badlink)
            mySpider.log ('     ' + '\n     '.join(mySpider.viewedQueue[badlink]))
            
    #print mySpider.badlinks
    mySpider.log("\nAll links found")
    mySpider.log('    ' + "%s" % "\n    ".join(sorted(mySpider.viewedQueue.keys())))
if __name__ == "__main__":
    main()