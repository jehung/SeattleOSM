import xml.etree.ElementTree as ET
import xml.etree.cElementTree as ET
import pprint
import pickle
from collections import defaultdict
import re

OSM_FILE = "seattle_washington.osm"
SAMPLE_FILE = "test.osm"
bounds_subtags = []
member_subtags = []
nd_subtags = []
node_subtags = []
osm_subtags = []
relation_subtags = []
tag_subtags = []
way_subtags = []

# First, understand the dataset by taking every k-th top level element
# Parameter: take every k-th top level element
k = 5000


def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag

    Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


with open(SAMPLE_FILE, 'wb') as output:
    output.write('<?xml version="1.0" encoding="UTF-8"?>\n'.encode('utf-8'))
    output.write('<osm>\n  '.encode('utf-8'))

    # Write every kth top level element
    for i, element in enumerate(get_element(OSM_FILE)):
        if i % k == 0:
            output.write(ET.tostring(element, encoding='utf-8'))

    output.write('</osm>'.encode('utf-8'))


def count_tags(filename):
    tags = {}

    for event, elem in ET.iterparse(filename):
        if elem.tag not in tags:
            tags[elem.tag] = 1
        else:
            tags[elem.tag] += 1

    return tags


tags = count_tags('seattle_washington.osm')

with open('tags.pickle', 'wb') as tagsPickle:
    pickle.dump(tags, tagsPickle, protocol=pickle.HIGHEST_PROTOCOL)

with open('tags.pickle', 'rb') as tagsPickle:
    unserialized_tags = pickle.load(tagsPickle)

for _, element in ET.iterparse('seattle_washington.osm'):
    if element.tag == 'bounds' and element.attrib.keys() not in bounds_subtags:
        bounds_subtags.append(element.attrib.keys())
    elif element.tag == 'member' and element.attrib.keys() not in member_subtags:
        member_subtags.append(element.attrib.keys())
    elif element.tag == 'nd' and element.attrib.keys() not in nd_subtags:
        nd_subtags.append(element.attrib.keys())
    elif element.tag == 'node' and element.attrib.keys() not in node_subtags:
        node_subtags.append(element.attrib.keys())
    elif element.tag == 'osm' and element.attrib.keys() not in osm_subtags:
        osm_subtags.append(element.attrib.keys())
    elif element.tag == 'relation' and element.attrib.keys() not in relation_subtags:
        relation_subtags.append(element.attrib.keys())
    elif element.tag == 'tag' and element.attrib.keys() not in tag_subtags:
        tag_subtags.append(element.attrib.keys())
    elif element.tag == 'way' and element.attrib.keys() not in way_subtags:
        way_subtags.append(element.attrib.keys())
    else:
        pass

# We now proceed with the address cleaning.
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road",
            "Trail", "Parkway", "Commons"]


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)


def audit(osmfile):
    osm_file = open('seattle_washington.osm', 'r', encoding='cp1252', errors='replace')
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=('start',)):
        if elem.tag == 'node' or elem.tag == 'way':
            for tag in elem.iter('tag'):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types


st_types = audit(OSM_FILE)

# The above Python dictionary shows the entire collection of street types after we have done our initial cleaning. Now we see that a vast majority of street types no longer bears problems. However, some of the street types are obviously wrong. Most notably, whenever **Suite number / apartment number** is present in the street name, the code has confused it with the name of the street. This needs our attention.
#
# To address this problem, we should make sure that our subsequent code to clean and wrangle the OSM data will shape the raw data in such a way that will avoid confusing the suite number / apartment number with the street name. A convenient way to achieve this is to present an address in the JSON document (namely, the cleaned file) with schema such as this:
#
# "address": {"street": "3401 Evanston Ave N, Suite A"}

mapping = {"St": "Street",
           "St.": "Street",
           "Ave": "Avenue",
           "Rd.": "Road",
           "Ave.": "Avenue"
           }


def update_name(name, mapping):
    m = street_type_re.search(name)
    street_type = m.group()

    name = re.sub(street_type, mapping[street_type], name)
    return name


mapping

# Now, prepaing the Data for Dababase Insertion


# !/usr/bin/env python

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
address_regex = re.compile(r'^addr\:')
street_regex = re.compile(r'^street')

CREATED = ["version", "changeset", "timestamp", "user", "uid"]


def shape_element(element):
    node = {}
    position_attributes = ['lat', 'lon']
    created_attributes = CREATED

    if element.tag == "node" or element.tag == "way":
        # populate tag type
        node['type'] = element.tag

        # initialize address
        address = {}

        # parse through attributes
        for attribute in element.attrib:
            if attribute in CREATED:
                if 'created' not in node:
                    node['created'] = {}
                node['created'][attribute] = element.get(attribute)
            elif attribute in position_attributes:
                continue
            else:
                node[attribute] = element.get(attribute)

        # populate position
        if 'lat' in element.attrib and 'lon' in element.attrib:
            node['pos'] = [float(element.get('lat')), float(element.get('lon'))]

        # parse second-level tags for nodes
        for child in element:
            # parse second-level tags for ways and populate `node_refs`
            if child.tag == 'nd':
                if 'node_refs' not in node:
                    node['node_refs'] = []
                if 'ref' in child.attrib:
                    node['node_refs'].append(child.get('ref'))

            # throw out not-tag elements and elements without `k` or `v`
            if child.tag != 'tag' or 'k' not in child.attrib or 'v' not in child.attrib:
                continue
            key = child.get('k')
            val = child.get('v')

            # skip problematic characters
            if problemchars.search(key):
                continue

            # parse address k-v pairs
            elif address_regex.search(key):
                key = key.replace('addr:', '')
                address[key] = val


            # catch-all
            else:
                node[key] = val
        # compile address
        if len(address) > 0:
            node['address'] = {}
            street_full = None
            street_dict = {}
            street_format = ['prefix', 'name', 'type']
            # parse through address objects
            for key in address:
                val = address[key]
                if street_regex.search(key):
                    if key == 'street':
                        street_full = update_name(val, mapping) if val in mapping else val
                    elif 'street:' in key:
                        street_dict[key.replace('street:', '')] = update_name(val, mapping) if val in mapping else val
                else:
                    node['address'][key] = update_name(val, mapping) if val in mapping else val
            # assign street_full or fallback to compile street dict
            if street_full:
                node['address']['street'] = update_name(street_full, mapping) if street_full in mapping else street_full
            elif len(street_dict) > 0:
                node['address']['street'] = ' '.join([street_dict[key] for key in street_format])
        return node
    else:
        return None


def process_map(file_in, pretty=False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2) + "\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data


data = process_map('seattle_washington.osm')
