import json
import string
import sys
import urllib2

rawInput = sys.argv[1]
key = "5974948d3baa3d1cabc4eb00e4099e3d785d43df"
options = [
  'include-passage-references=false',
  'include-first-verse-numbers=false',
  'include-verse-numbers=false',
  'include-footnotes=false',
  'include-footnote-body=false',
  'include-short-copyright=false',
  'include-passage-horizontal-lines=false',
  'include-heading-horizontal-lines=false',
  'include-headings=false',
  'include-selahs=false',
  'indent-paragraphs=0',
  'indent-poetry=false',
  'indent-poetry-lines=0',
  'indent-declares=0',
  'indent-psalm-doxology=0'
]
options = '&'.join(options)

baseUrl = 'https://api.esv.org/v3/passage/text/'

passage = '+'.join(rawInput.split())

url = baseUrl + '?q=%s&%s' % (passage, options)
# print url
req = urllib2.Request(url)
req.add_header('Accept', 'application/json')
req.add_header('Authorization', 'Token ' + key)

resp = urllib2.urlopen(req)
content = json.load(resp)
# print content

if content['canonical'] == '' or len(content['passages']) > 1:
  errorOutput = {"items":[{"title":rawInput, "subtitle":"No passage found", "icon":"icon.png"}]}
  print json.dumps(errorOutput)

else:
  passageRef = content['canonical']
  pageSplit = content['passages'][0].split('\n\n')
  passage = ' '.join(pageSplit).rstrip()
  # print passage
  passageWithRef = passage + ' (' + passageRef + ' ESV)'
  data = {'items':[{'arg':passageWithRef, 'valid':'YES', 'autocomplete':passageRef, 'title':passageRef, 'subtitle':passage, 'icon':'icon.png'}]}
  print json.dumps(data)