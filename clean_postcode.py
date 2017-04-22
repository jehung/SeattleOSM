import xml.etree.ElementTree as ET
import xml.etree.cElementTree as ET
import pprint
import pickle
from collections import defaultdict
import re



# We now proceed with the address cleaning.
OSM_FILE = "seattle_washington.osm"
postcode_re = re.compile(r'^\d{5}$')
expected_postcode = set(["98072", "98053", "98074", "98075", "98027", "98059", "98366", "98311", "98383",
            "98370", "98115", "98125", "98034", "98103", "98201"])



## The following audits the postcodes
def is_postcode(elem):
    return (elem.attrib['k'] == "addr:postcode")


def audit_postcode_type(current, bad_codes, expected_postcode):
    ## logic1: if postode not digit but contains postcode_re, take postcode_re as postcode
    ## logic2: else add current to bad_codes
    ## logic3: if postcode starts with 9, add to expected_codes
    ## logic4: otherwise, check if postcode_re starts with 9; if postcode_re starts with 9, add to expeted_codes
    ## logic5: postcode is either len 5 or len 9

    if not current.isdigit():
        bad_codes.append(current)
    elif len(current) != 5:
        bad_codes.append(current)
    elif not current.startswith('9'):
        bad_codes.append(current)
    else:
        expected_postcode.update(current)


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

print error_codes