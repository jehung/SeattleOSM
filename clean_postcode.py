import xml.etree.ElementTree as ET
import xml.etree.cElementTree as ET
import pprint
import pickle
from collections import defaultdict
import re



# We now proceed with the address cleaning.
OSM_FILE = "seattle_washington.osm"
postcode_re5 = re.compile(r'\d{5}$')
postcode_re9 = re.compile(r'^(\d{5})-\d{4}$')


#expected_postcode = set(["98072-0000", "98053-0000", "98074-0000", "98075-0000", "98027-0000", "98059-0000",
#                         "98366-0000", "98311-0000", "98383-0000", "98370-0000", "98115-0000", "98125-0000",
#                         "98034-0000", "98103-0000", "98201-0000"])

expected_postcode = []



## The following audits the postcodes
def is_postcode(elem):
    return (elem.attrib['k'] == "addr:postcode")


def audit_postcode_type(current, bad_codes, expected_postcode):
    ## logic1: if postode not digit but contains postcode_re, take postcode_re as postcode
    ## logic2: else add current to bad_codes
    ## logic3: if postcode starts with 9, add to expected_codes
    ## logic4: otherwise, check if postcode_re starts with 9; if postcode_re starts with 9, add to expeted_codes
    ## logic5: postcode is either len 5 or len 9


    m = re.search(postcode_re5, current)
    if m:
        current = m.group()+'-0000'



        #if postcode_re9.search(current):
        #    current = re.sub(postcode_re9, current)
        #    #bad_codes.append(current)
        #if postcode_re5.search(current):
        #    current = str(re.findall(postcode_re5, current))+'-0000'


    if current.startswith('9'):
        if current not in expected_postcode:
            expected_postcode.append(current)
        print 'good', current
    else:
        if current not in bad_codes:
            bad_codes.append(current)
            print 'bad', current


def audit_postcode(osmfile):
    osm_file = open(OSM_FILE, 'r')
    bad_codes = []
    #expected_postcode = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_postcode(tag):
                    audit_postcode_type(tag.attrib["v"], bad_codes, expected_postcode)
    return bad_codes, expected_postcode


error_codes, expected_postcode = audit_postcode(OSM_FILE)

#print error_codes
#print expected_postcode