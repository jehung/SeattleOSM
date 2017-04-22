import xml.etree.ElementTree as ET
import xml.etree.cElementTree as ET
from collections import defaultdict
import re


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
address_regex = re.compile(r'^addr\:')
street_regex = re.compile(r'^street')

CREATED = ["version", "changeset", "timestamp", "user", "uid"]


st_types = audit(OSM_FILE)

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
