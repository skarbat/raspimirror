#!/usr/bin/env python
#
# Helper module that fetches a list of the official MagicMirror 3rd party modules.
#

import sys
import re
import urllib2

def get_mm_modules(url='https://github.com/MichMich/MagicMirror/wiki/MagicMirror-Modules'):
    '''
    Returns a list of MagicMirror 3rd party modules from the official Wiki page
    '''
    urls=[]
    content = urllib2.urlopen(url).readlines()

    for line in content:
        try:
            r = re.search('^(<p><strong><a href=\")(http.*)\">(.*)', line.strip())
            if r:
                # FIXME: some urls are not extracted correctly
                url=r.groups()[1].strip('/')
                garbage=url.find('"')
                if garbage != -1:
                    url = url[:garbage]
                urls.append(url)
        except:
            pass

    return urls


if __name__ == '__main__':

    modules=get_mm_modules()
    for m in modules:
        print m

    if len(sys.argv) > 1 and sys.argv[1] == '--verbose':
        print '{} modules found'.format(len(modules))
        
    sys.exit(0)
