# -*- coding: utf-8 -*-
# pylint: disable=E1101

import clr
clr.AddReferenceByPartialName('System.Xml')
clr.AddReferenceByPartialName('System.IO')
clr.AddReferenceByPartialName('RhinoPythonHost')
clr.AddReferenceByPartialName('Grasshopper')
from System.Xml import XmlReader, XmlNodeType
from System.IO import File
import re
import math
import Grasshopper
import Rhino
import RhinoPython.Host as _rhinopythonhost
import scriptcontext


class OsmXmlFileParser(object):


    def __init__(self, fileloc=None, options={}, progress=None):
        self.file_location = fileloc
        self.bounds = self.Bounds()
        self.nodes = {}
        self.ways = {}
        self.relations = {}
        self.options = {'load_nodes': True, # <node>
                        'load_ways': True, # <way>
                        'load_relations': True, # <relation>
                        # elements inside a node, way, relation entity
                        'load_node_subtree': True, # <tag>
                        'load_way_subtree': True, # <nd>, <tag>
                        'load_relation_subtree': True, # <member>, <tag>
                        # node, way, relation entities have same attributes
                        'load_additional_attr': False, # switch for attr. below
                        'load_visible_attr': False,
                        'load_version_attr': False,
                        'load_changeset_attr': False,
                        'load_timestamp_attr': False,
                        'load_user_attr': False,
                        'load_uid_attr': False
                        }
        self.options.update(options)
        self.progress = progress
        self.__read()


    def __readAttr(self, xml, attr_name):
        if xml.HasAttributes and xml.MoveToAttribute(attr_name):
            attr_value = xml.Value
            xml.MoveToElement()
            return attr_value


    def __readOsmSubtreeEntities(self, xml):
        way_nodes = [] # list datatype to keep order of osm nodes
        rel_members = [] # list datatype to keep order of osm members
        tags = {}

        inner = xml.ReadSubtree()
        while inner.Read():
            if inner.Name in ('nd', 'member', 'tag') and \
                    inner.NodeType == XmlNodeType.Element:

                if inner.Name == 'nd':
                    ref_id = int(self.__readAttr(xml, 'ref'))
                    way_nodes.append(ref_id)

                elif inner.Name == 'member':
                    typ = self.__readAttr(xml, 'type')
                    ref_id = int(self.__readAttr(xml, 'ref'))
                    role = self.__readAttr(xml, 'role')
                    rel_members.append(self.RelationMember(typ, ref_id, role))

                elif inner.Name == 'tag':
                    key = self.__readAttr(xml, 'k')
                    value = self.__readAttr(xml, 'v')
                    tags[key] = value
        inner.Close()

        if xml.Name == 'node':
            return {}, tags

        elif xml.Name == 'way':
            return way_nodes, tags

        elif xml.Name == 'relation':
            return rel_members, tags


    def __readOsmEntities(self, xml):
        # self.load_nodes looks better than self.options['load_nodes']
        for key, value in self.options.iteritems():
            setattr(self, key, value)

        # read xml element; bounds
        while xml.Read():
            if xml.IsStartElement('bounds'):
                self.bounds = self.Bounds(
                    minlat=float(self.__readAttr(xml, 'minlat')),
                    minlon=float(self.__readAttr(xml, 'minlon')),
                    maxlat=float(self.__readAttr(xml, 'maxlat')),
                    maxlon=float(self.__readAttr(xml, 'maxlon'))
                )
            break # bounds element exist only once.

        # read xml elements; node, way, relation
        while xml.Read():

            if scriptcontext.id == 1 and _rhinopythonhost.EscapePressed(reset=True):
                print('loading aborted')
                self.__dispose()
                break
            elif scriptcontext.id == 2 and Grasshopper.Kernel.GH_Document.IsEscapeKeyDown():
                print('loading aborted')
                self.__dispose()
                break

            for entity in ['node', 'way', 'relation']:
                if xml.IsStartElement(entity):

                    # --- attributes for all entities; node, way, relation ---

                    if self.load_additional_attr:
                        attr = self.Attributes()

                        if self.load_visible_attr:
                            attr.visible = self.__readAttr(xml, 'visible')
                        if self.load_version_attr:
                            attr.version = self.__readAttr(xml, 'version')
                        if self.load_changeset_attr:
                            attr.changeset = self.__readAttr(xml, 'changeset')
                        if self.load_timestamp_attr:
                            attr.timestamp = self.__readAttr(xml, 'timestamp')
                        if self.load_user_attr:
                            attr.user = self.__readAttr(xml, 'user')
                        if self.load_uid_attr:
                            attr.uid = self.__readAttr(xml, 'uid')
                    else:
                        attr = None

                    # --- entities node, way, relation ---

                    if entity == 'node':
                        if self.load_nodes:
                            element_id = int(self.__readAttr(xml, 'id'))
                            lat = float(self.__readAttr(xml, 'lat'))
                            lon = float(self.__readAttr(xml, 'lon'))
                            if self.load_node_subtree:
                                _, tags = self.__readOsmSubtreeEntities(xml)
                                node = self.Node(lat, lon, attr, tags)
                                self.nodes[element_id] = node
                            else:
                                node = self.Node(lat, lon, attr, {})
                                self.nodes[element_id] = node

                    elif entity == 'way':
                        if self.load_ways:
                            element_id = int(self.__readAttr(xml, 'id'))
                            if self.load_way_subtree:
                                way_nodes, tags = \
                                    self.__readOsmSubtreeEntities(xml)
                                way = self.Way(way_nodes, attr, tags)
                                self.ways[element_id] = way
                            else:
                                self.ways[element_id] = self.Way({}, attr, {})

                    elif entity == 'relation':
                        if self.load_relations:
                            element_id = int(self.__readAttr(xml, 'id'))
                            if self.load_relation_subtree:
                                rel_members, tags = \
                                    self.__readOsmSubtreeEntities(xml)
                                relation = self.Relation(
                                                        rel_members, attr, tags)
                                self.relations[element_id] = relation
                            else:
                                relation = self.Relation({}, attr, {})
                                self.relations[element_id] = relation

            self.progress.updateFromFilestream() if self.progress else None


    def __read(self):
        try:
            filestream = File.OpenRead(self.file_location)
            xml = XmlReader.Create(filestream)
            if self.progress:
                self.progress.filestream = filestream
        except IOError as e:
            raise e
        else:
            if xml.IsStartElement('osm'):
                self.__readOsmEntities(xml)
            else:
                print('Osm file is not valid. No <osm> element found.\n')
        finally:
            if File.Exists(self.file_location):
                xml.Close()
                filestream.Close()


    def __dispose(self):
        self.nodes = {}
        self.ways = {}
        self.relations = {}
        if self.progress:
            self.progress.close()


    def statistic(self):
        print(self.file_location)
        print('Bounds(minlat={}, minlon={}, maxlat={}, maxlon={})'.format(
            self.bounds.minlat, self.bounds.minlon, 
            self.bounds.maxlat, self.bounds.maxlon)
            )
        print('osmxml | Nodes:{}, Ways:{}, Relations:{}' \
            .format(len(self.nodes), len(self.ways), len(self.relations)))


    class Bounds(object):

        def __init__(self, minlat=0, minlon=0, maxlat=0, maxlon=0):
            self.minlat = minlat
            self.minlon = minlon
            self.maxlat = maxlat
            self.maxlon = maxlon


        def __repr__(self):
            s = 'Bounds(minlat={}, minlon={}, maxlat={}, maxlon={})'
            return s.format(self.minlat, self.minlon, self.maxlat, self.maxlon)


    class Attributes(object):

        def __init__(self, visible=None, version=None, changeset=None, 
                     timestamp=None, user=None, uid=None):
            self.visible = visible
            self.version = version
            self.changeset = changeset
            self.timestamp = timestamp
            self.user = user
            self.uid = uid


        def __repr__(self):
            class_vars = vars(self)
            att = dict((k,v) for k,v in class_vars.iteritems() if v is not None)
            return 'Attributes({})'.format(att)


    class Node(object):

        def __init__(self, latitude, longitude, attributes, tags):
            # id ; int
            self.latitude = latitude
            self.longitude = longitude
            self.attributes = attributes
            self.tags = tags


        def __repr__(self):
            return 'Node(latitude={}, longitude={}, attributes={}, tags={})' \
              .format(self.latitude, self.longitude, self.attributes, self.tags)


    class Way(object):

        def __init__(self, node_refs, attributes, tags):
            self.node_refs = node_refs # node ids
            self.attributes = attributes
            self.tags = tags


        def __repr__(self):
            return 'Way(node_refs={}, attributes={}, tags={})' \
                .format(self.node_refs, self.attributes, self.tags)


    class Relation(object):

        def __init__(self, members, attributes, tags):
            self.members = members
            self.attributes = attributes
            self.tags = tags


        def __repr__(self):
            return 'Relation(members={}, attributes={}, tags={})' \
                .format(self.members, self.attributes, self.tags)


    class RelationMember(object):

        def __init__(self, typ, ref_id, role):
            self.typ = typ
            self.ref_id = ref_id
            self.role = role


        def __repr__(self):
            return 'RelationMember(typ={}, ref_id={}, role={})' \
                .format(self.typ, self.ref_id, self.role)


class OsmObjects(object):


    def __init__(self, osmxml):
        self.osmxml = osmxml
        self.__recursive_relation_ids = []
        self.__used_way_ids = []
        self.__used_node_ids = []
        self.relations = self.__readRelations(osmxml)
        self.ways = self.__readWays(osmxml)
        self.nodes = self.__readNodes(osmxml)


    def __recursiveMembers(self, relation):
        stack = [relation]
        members = []
        recursive_relations = set()
        recursive_relation_ids = []

        while stack:
            current_relation = stack.pop(0)

            while stack and current_relation in recursive_relations:
                current_relation = stack.pop(0) # avoid endless loop, pop item
                # raise Exception('recursion loop in relation')
            recursive_relations.add(current_relation)

            for member in current_relation.members:
                if member.typ == 'relation':
                    if self.osmxml.relations.get(member.ref_id):
                        recursive_relation_ids.append(member.ref_id)
                        stack.append(self.osmxml.relations.get(member.ref_id))
                    else:
                        # 'relation {} not found in xml'.format(member.ref_id)
                        pass
                else:
                    members.append(member)

        return recursive_relation_ids, members


    def __readRelations(self, osmxml):
        relations = []
        for rel_id, relation in osmxml.relations.iteritems():
            relation.id = rel_id
            relation.ways = []
            relation.nodes = []

            # recursively collect all members within a relation
            recursive_relation_ids, members = self.__recursiveMembers(relation)
            self.__recursive_relation_ids.extend(recursive_relation_ids)
            relation.members = members
            
            for member in relation.members:
                if member.typ == 'node':
                    node = osmxml.nodes.get(member.ref_id)
                    if member.ref_id not in self.__used_node_ids:
                        self.__used_node_ids.append(member.ref_id)
                    if node:
                        node.id = member.ref_id
                        relation.nodes.append(node)
                    else:
                        # 'node {} not found in xml'.format(member.ref_id)
                        pass

                elif member.typ == 'way':
                    way = osmxml.ways.get(member.ref_id)
                    if member.ref_id not in self.__used_way_ids:
                        self.__used_way_ids.append(member.ref_id)
                    if way:
                        self.__used_node_ids.extend(way.node_refs)
                        way.id = member.ref_id
                        way.role = member.role
                        relation.ways.append(way)
                    else:
                        # 'way {} not found in xml'.format(member.ref_id)
                        pass

                elif member.typ == 'relation':
                    # 'not possible | recursively collected all members'
                    pass

                else:
                    # 'unknown member.typ | is not node, way, relation'
                    pass
        
            # append relation only if it contains nodes or ways
            if relation.nodes or relation.ways:
                relations.append(relation)

        # no duplicates. take only relation not relations inside a relation.
        r = [r for r in relations if r.id not in self.__recursive_relation_ids]

        return r


    def __readWays(self, osmxml):
        ways = []
        self.__used_way_ids = set(self.__used_way_ids)
        for way_id, way in osmxml.ways.iteritems():
            if way_id not in self.__used_way_ids:
                self.__used_node_ids.extend(way.node_refs)
                way.id = way_id
                # append way only if it contains at least 2 node_refs (line)
                if len(way.node_refs) >= 2:
                    ways.append(way)
            else:
                # '{} way already used by a relation'.format(way_id)
                pass

        return ways


    def __readNodes(self, osmxml):
        nodes = []
        self.__used_node_ids = set(self.__used_node_ids)
        for node_id, node in osmxml.nodes.iteritems():
            if node_id not in self.__used_node_ids:
                node.id = node_id
                # append node only if it contains lat/lon location
                if node.latitude and node.longitude:
                    nodes.append(node)
            else:
                # '{} node already used by a relation'.format(node_id)
                pass

        return nodes


    def statistic(self):
        print('osmobj | Nodes:{}, Ways:{}, Relations:{}' \
            .format(len(self.nodes), len(self.ways), len(self.relations)))


class OsmGeometry(object):


    def __init__(self, osmxml, osmobj):
        self.osmxml = osmxml
        self.osmobj = osmobj
        self.nodes = self.points(osmobj)
        self.ways = self.polygon(osmobj)
        self.relations = self.multipolygon(osmobj)
        

    def geometryAttributes(self, osm_entity):
        attr = {}

        ##### heights and levels
        for item in ['height', 'min_height', 'levels', 'min_level']:
            value = osm_entity.tags.get(item)
            if value:
                attr[item] = value

            item = 'building:' + item
            value = osm_entity.tags.get(item)
            if value:
                attr[item] = value

        ##### roof
        for item in ['height', 'shape']:
            item = 'roof:' + item
            value = osm_entity.tags.get(item)
            if value:
                attr[item] = value

        return attr


    def keyOrValueInTags(self, tags, search_str=''):
        # <tag k="building" v="yes"/> or <tag k="type" v="building"/>
        for k, v in tags.iteritems():
            if search_str in k or search_str == v:
                return True
        return False


    def getNodePoint(self, node_id):
        node = self.osmxml.nodes.get(node_id)
        if node:
            lat, lon = node.latitude, node.longitude
            x, y = Mercator.degreesToMeter(lat, lon)
            return Rhino.Geometry.Point3d(x, y, 0)


    def getWayPoints(self, way_id):
        way = self.osmxml.ways.get(way_id)
        points = []
        for node_id in way.node_refs:
            pt = self.getNodePoint(node_id)
            points.append(pt) if pt else None

        if len(points) >= 2: # at least a line
            return points


    def getCurve(self, way_id):
        pts = self.getWayPoints(way_id)
        rh_crv = Rhino.Geometry.Curve.CreateControlPointCurve(pts, 1)
        
        return rh_crv


    def extrusionHeight(self, way, floor2floor=3.8):
        f2f = floor2floor # floor-to-floor height in meter

        def geom_unit(item):
            value_str = way.geom_attr.get(item) 
            if not value_str:
                value_str = way.geom_attr.get('building:'+item)

            if value_str:
                value_meter = self.OsmUnit(value_str).get()
                return value_meter
            else:
                return 0

        min_height = geom_unit('min_height')
        height = geom_unit('height')
        min_level = geom_unit('min_level')
        levels = geom_unit('levels')
        roof_height = geom_unit('roof_height')

        if height and min_height:
            if height - (min_height + roof_height) == 0:
                height = height + roof_height
            ext_start = min_height
            ext_height = height - min_height - roof_height

        elif height:
            ext_start = 0
            ext_height = height - roof_height

        elif levels and min_level and min_height:
            ext_start = min_height
            ext_height = (levels * f2f) - (min_level * f2f) - roof_height

        elif levels and min_level:
            ext_start = min_level * f2f
            ext_height = (levels * f2f) - (min_level * f2f) - roof_height

        elif levels:
            ext_start = 0
            ext_height = (levels * f2f) - roof_height

        else:
            ext_start = 0
            ext_height = 0

        return ext_start, ext_height


    def multipolygon(self, osmobj):
        for relation in osmobj.relations:
            relation.buildings2d = self.MultiPolygon(self) # no height attr
            relation.buildings3d = self.MultiPolygon(self)
            relation.objects2d = self.MultiPolygon(self) # no height attr
            relation.objects3d = self.MultiPolygon(self)

            for way in relation.ways:
                geom_attr = self.geometryAttributes(relation)
                geom_attr.update(self.geometryAttributes(way))
                way.geom_attr = geom_attr

                if self.keyOrValueInTags(way.tags, search_str='building') \
                or self.keyOrValueInTags(relation.tags, search_str='building'):
                    
                    if geom_attr: # 3d building
                        if way.role == 'inner':
                            relation.buildings3d.inner_ways.append(way)
                        else:
                            relation.buildings3d.outer_ways.append(way)
                    
                    else:  # 2d multipolygon building
                        if way.role == 'inner':
                            relation.buildings2d.inner_ways.append(way)
                        else:
                            relation.buildings2d.outer_ways.append(way)
                else: 
                    
                    if geom_attr: # 3d objects e.g. fountain, wall, ...
                        if way.role == 'inner':
                            relation.objects3d.inner_ways.append(way)
                        else:
                            relation.objects3d.outer_ways.append(way)
                    
                    else: # 2d multipolygon
                        if way.role == 'inner':
                            relation.objects2d.inner_ways.append(way)
                        else:
                            relation.objects2d.outer_ways.append(way)

            for node in relation.nodes:
                node.point = self.getNodePoint(node.id)

        return osmobj.relations


    def polygon(self, osmobj):
        for way in osmobj.ways:
            way.buildings2d = self.MultiPolygon(self) # no height attr
            way.buildings3d = self.MultiPolygon(self)
            way.objects2d = self.MultiPolygon(self) # no height attr
            way.objects3d = self.MultiPolygon(self)
            
            geom_attr = self.geometryAttributes(way)
            way.geom_attr = geom_attr

            if self.keyOrValueInTags(way.tags, search_str='building'):
                if geom_attr: # 3d building
                    way.buildings3d.outer_ways.append(way)
                else:  # 2d polygon building
                    way.buildings2d.outer_ways.append(way)
            else: 
                if geom_attr: # 3d objects e.g. fountain, wall, ...
                    way.objects3d.outer_ways.append(way)
                else: # 2d polygon
                    way.objects2d.outer_ways.append(way)

        return osmobj.ways


    def points(self, osmobj):
        for node in osmobj.nodes:
            rh_point = self.getNodePoint(node.id)
            node.point = rh_point

        return osmobj.nodes


    class OsmUnit(object):


        units = {'m': 1, 'km': 1000, 'mi': 1609.344, 'nmi': 1852,
                        'feet': 0.3048, 'inch': 0.0254}


        def __init__(self, txt):
            self.txt = str(txt)


        def regex_match(self, regex):
            match = re.search(regex, self.txt)
            return match.groups() if match else None


        def unit_prefix(self):
            if "'" in self.txt and '"' in self.txt:
                return 'feet'
            elif "'" in self.txt:
                return 'feet'
            elif '"' in self.txt:
                return 'inch'
            else:
                match = self.regex_match(r'([A-Za-z]{1,3})')
                if match and match[0] in self.units:
                    key = match[0]
                    value = self.units[key]
                    return key
            return ''


        def unit_conversion(self, value, unit):
            if unit in self.units:
                fac = self.units[unit]
                value_meter = value * fac
                return value_meter
            else:
                # 'unit not definded'
                return value


        def txt_2_float(self, unit):
            if unit == 'feet' or unit ==  'inches':
                match = self.regex_match(r'(\d{0,})\'?\"?(\d{0,})')

                if match[0] and match[1]:
                    ft = float(match[0])
                    inches = float(match[1])
                    ft = ft + inches * 1.0 / 12.0
                    return ft

                elif match[0]:
                    ft = float(match[0])
                    return ft

                elif match[1]:
                    inches = float(match[1])
                    ft = inches * 1.0 / 12.0
                    return ft

                else:
                    return 0.0

            else:
                chars = re.findall(r'[A-Za-z]', self.txt)
                chars.extend(["'", "''", '"', ' '])
                for c in chars:
                    self.txt = self.txt.replace(c, '')
                self.txt = self.txt.replace(',', '.')

                try:
                    return float(self.txt)
                except:
                    return 0.0


        def get(self):
            unit = self.unit_prefix() # feet, inch, m, ...
            value = self.txt_2_float(unit)
            value_meter = self.unit_conversion(value, unit)
            return value_meter



    class MultiPolygon(object):

        def __init__(self, osmgeo):
            self.osmgeo = osmgeo
            self.outer_ways = []
            self.inner_ways = []


        def extrude(self, outer_rhcrv, inner_rhcrvs=[], ext_start=0, 
                    ext_height=1, cap=True):

            if ext_start-ext_height == 0 or ext_height == 0:
                return
            extrusion = Rhino.Geometry.Extrusion()
            extrusion.SetOuterProfile(outer_rhcrv, cap)
            for ic in inner_rhcrvs:
                extrusion.AddInnerProfile(ic)
            start_pt = Rhino.Geometry.Point3d(0, 0, ext_start)
            end_pt = Rhino.Geometry.Point3d(0, 0, ext_start + ext_height)
            vec = Rhino.Geometry.Vector3d(0, 1, 1)
            extrusion.SetPathAndUp(start_pt, end_pt, vec)

            return extrusion


        def __joinWays(self, ways):
            # TODO join ways with same tags
            # raise NotImplementedError()
            pass


        def __getCurves(self, ways):
            rh_curves = []
            _ways = []
            for way in ways:
                pts = self.osmgeo.getWayPoints(way.id)
                rh_crv = Rhino.Geometry.Curve.CreateControlPointCurve(pts, 1)
                if rh_crv:
                    rh_curves.append(rh_crv)
                    _ways.append(way)
            
            return _ways, rh_curves


        def getCurves(self):
            outer_ways, outer_crvs = self.__getCurves(self.outer_ways)
            inner_ways, inner_crvs = self.__getCurves(self.inner_ways)

            return inner_ways, inner_crvs, outer_ways, outer_crvs


        def getExtrusions(self, floor2floor=3.8):

            # TODO join ways with same tags
            # outer_ways = __joinWays(outer_ways)
            # inner_ways = __joinWays(inner_ways)

            rh_extrusions = []
            if self.outer_ways and self.inner_ways:

                if len(self.outer_ways) == 1:
                    way = self.outer_ways[0]
                    outer_crv = self.osmgeo.getCurve(way.id)

                    if outer_crv.IsClosed:
                        # inner-crvs in outer-crv check
                        inner_crvs = [self.osmgeo.getCurve(way.id) 
                                      for way in self.inner_ways
                                     ]
                        inner_crvs = [
                            crv for crv in inner_crvs if crv.IsClosed and 
                         int(Rhino.Geometry.Curve.PlanarClosedCurveRelationship(
                         outer_crv, crv, Rhino.Geometry.Plane.WorldXY, 0)) == 3
                        ]

                        es, eh = self.osmgeo.extrusionHeight(way, floor2floor)
                        rh_ex = self.extrude(outer_crv, inner_crvs, 
                                          ext_start=es, ext_height=eh, cap=True)
                        if rh_ex:
                            rh_extrusions.append(rh_ex)

                else:
                    # TODO sort multiple outer_ways and inner_ways
                    # raise NotImplementedError()
                    pass

            elif self.outer_ways or self.inner_ways:
                
                for ways in [self.outer_ways, self.inner_ways]:
                    for way in ways:
                        crv = self.osmgeo.getCurve(way.id)

                        if crv.IsClosed:
                            es, eh = self.osmgeo.extrusionHeight(way)
                            rh_ex = self.extrude(crv, ext_start=es, 
                                                    ext_height=eh, cap=True)
                            if rh_ex:
                                rh_extrusions.append(rh_ex)

            return  rh_extrusions


class Mercator(object):
    # Pseudo-Web-Mercator
    # http://wiki.openstreetmap.org/wiki/Mercator#Python

    earth_radius = 6378137.0


    @staticmethod
    def yToLat(y):
        lat = math.degrees(math.atan(math.exp(y/Mercator.earth_radius))*2.0 - math.pi/2.0)
        return lat


    @staticmethod
    def xToLon(x):
        lon = math.degrees(x/Mercator.earth_radius)
        return lon


    @staticmethod
    def latToY(lat):
        if lat > 89.5 : lat = 89.5
        if lat < -89.5 : lat = -89.5
        y = math.log(math.tan(math.pi/4.0 + math.radians(lat)/2.0))*Mercator.earth_radius
        return y


    @staticmethod
    def lonToX(lon):
        x = math.radians(lon)*Mercator.earth_radius
        return x


    @staticmethod
    def meterToDegrees(x, y):
        lon = Mercator.xToLon(x)
        lat = Mercator.yToLat(y)
        return lat, lon


    @staticmethod
    def degreesToMeter(lat, lon):
        x = Mercator.lonToX(lon)
        y = Mercator.latToY(lat)
        return x, y


class ProgressBar(object):


    def __init__(self, label='ProgressBar', lower=0, upper=100,
                 embed_label=True, show_percent=True):
        self.label = label
        self.lower = lower
        self.upper = upper
        self.embed_label = embed_label
        self.show_percent = show_percent
        # data from filestream
        self.filestream = None
        self.lastposition = 0


    def show(self):
        Rhino.UI.StatusBar.ShowProgressMeter(self.lower, self.upper,
                                             self.label, self.embed_label,
                                             self.show_percent
                                             )


    def update(self, position):
        self.show()
        Rhino.UI.StatusBar.UpdateProgressMeter(position, absolute=True)
        if position == self.upper:
            self.close()


    def updateFromFilestream(self):
        """Update progress of current filestream position from 0 to 100."""

        if self.lastposition != self.filestream.Position:
            self.lastposition = self.filestream.Position
            position = 100.0 * self.lastposition / self.filestream.Length
            self.update(position)


    def close(self):
        Rhino.UI.StatusBar.HideProgressMeter()
