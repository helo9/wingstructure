"""Module for representation of wing section's structure

This module defines classes which allow definition of a wing section as chain of multiple structure elements.
Definition of a structure starts with SectionBase, which stores airfoil coordinates. Beginning with this exterior
geometry structure elements can be added from out to inside. Possible Elements are Layers, covering the whole
surface, Reinforcements for higher stiffness locally and Spar elements (ISpar and BoxSpar).

Example
-------
.. code-block:: python

   import numpy as np
   from wingstructure import structure

   # Load cooardinates
   coords = np.loadtxt('ah93157.dat', skiprows=1) * 1.2
   sectionbase = structure.SectionBase(coords)

   # Define Material
   import collections
   Material = collections.namedtuple('Material', ['ρ'])

   carbonfabric = Material(1.225)
   foam = Material(1.225)
   sandwich = Material(1.225)

   # create layers
   outerlayer = structure.Layer(carbonfabric, 5e-4)
   core = structure.Layer(foam, 1e-2)
   innerlayer = structure.Layer(carbonfabric, 5e-4)

   # create Spar
   spar = structure.ISpar(material={'flange': carbonfabric, 'web': sandwich},
                          midpos=0.45,
                          flangewidth=0.2,
                          flangethickness=0.03,
                          webpos=0.5,
                          webthickness=0.02)

    # add to sectionbase
    sectionbase.extend([outerlayer, core, innerlayer, spar])

   # Analyse Mass
   massana = structure.MassAnalysis(sectionbase)
   cg, mass = massana.massproperties()
"""

from abc import ABC, abstractmethod
from functools import wraps

import numpy as np
from collections import namedtuple
from numpy.linalg import norm
from shapely import geometry as shpl_geom
from shapely import ops
from shapely.algorithms import cga

def _get_inside_direction(linearring):
    """Gets the inside direction for parallel offset (left or right)
    from signed area of geometry"""
    
    if cga.signed_area(linearring) > 0:
        return 'left'
    else:
        return 'right'

def _create_offset_box(line, thickness, side, bevel=0.0,
                        symmetric=False):
    
    offsetline = line.parallel_offset(thickness, side=side)
    
    if symmetric:
        offsetline2 = line.parallel_offset(thickness, side=_oderside(side))
        line = offsetline2

    if bevel > 0.0:
        
        raise Exception('Beveling not yet implemented')
    
    if side == 'left':
        connect1 = shpl_geom.LineString((line.coords[-1], offsetline.coords[-1]))
        connect2 = shpl_geom.LineString((line.coords[0], offsetline.coords[0]))
        return shpl_geom.Polygon(ops.linemerge((line, connect1, offsetline, connect2)))
    else:
        connect1 = shpl_geom.LineString((line.coords[-1],offsetline.coords[0]))
        connect2 = shpl_geom.LineString((line.coords[0], offsetline.coords[-1]))
        return shpl_geom.Polygon(ops.linemerge((offsetline,connect1,line,connect2)))

class _AbstractBaseStructure:
    def __init__(self, material):
        super().__init__()
        self.geometry = None  
        self.material = material
        self._cut_elements = []

        self.interior = None
        self.geometry = None
        self._updatecallback = None
    
    def _set_updatecallback(self, callback):
        if self._updatecallback is None:
            self._updatecallback = callback

    def _unset_updatecallback(self):
        self._updatecallback = None

    def _trigger_update(self):
        if self._updatecallback is not None:
            callback = self._updatecallback
            callback(self)

    @abstractmethod
    def _update_geometry(self, exterior):
        pass

    @property
    def massproperties(self):
        return (self.geometry.centroid, self.geometry.area*self.material.ρ)

    def area(self):
        return self.geometry.area

    @property
    def cut_elements(self):
        return self._cut_elements
    
    def exportgeometry(self, refpoint=np.zeros(2)):
        arraygeom = geom2array(self.geometry, refpoint)

        return [arraygeom._replace(material=self.material)]

def _updatedecorator(method):
    def wrappedcall(self, *args, **kwargs):
        method(self, *args, **kwargs)
        self._update()
    return wrappedcall

def _refine_interior(interior):
    
    if interior.type == 'MultiLineString':
        interior = shpl_geom.LinearRing(interior.geoms[0])
    else:
        interior = shpl_geom.LinearRing(interior)

    # find bugs in interior and remove them
    pts = np.array(interior)[:-1, :]
    del_pts = []

    for ii in range(len(pts)):
        vec1 = pts[ii]-pts[ii-1]
        vec2 = pts[(ii+1) % len(pts)]-pts[ii]
        
        if(np.linalg.norm(vec1/norm(vec1)+vec2/norm(vec2)) < 1e-3):
            del_pts.append(ii)

    pts2 = np.delete(pts, del_pts, axis=0)
    
    return shpl_geom.LinearRing(pts2)

class SectionBase:
    """Foundation for section's wing structure description

    Implements a list like interface for the assembling of wing section's interior.
    
    Parameters
    ----------
    airfoil_coordinates : np.ndarray
        airfoils coordinates from dat file
    
    Attributes
    ----------
    interior: shapely.geometry.LinearRing
        representation of airfoil as shapely geometry
    
    """

    def __init__(self, airfoil_coordinates):
        self._geometry = shpl_geom.LinearRing(airfoil_coordinates)
        self._features = []
        self._featuregeometries = []

    @_updatedecorator
    def append(self, featuredef):
        self._features.append(featuredef)

    @_updatedecorator
    def insert(self, index, newfeature):
        self._features.insert(index, newfeature)

    @_updatedecorator
    def extend(self, featuredefs):
        for featuredef in featuredefs:
            self.append(featuredef)

    @_updatedecorator
    def remove(self, featuredef):
        if featuredef not in self._features:
            raise Exception('No feature {} found.'.format(featuredef))

        self._features.remove(featuredef)

    @_updatedecorator
    def pop(self):
        self._features.pop()

    def _update_callback(self, updated_feature):
        try:
            first_idx = self._features.index(updated_feature) #TODO: Error handling
        except ValueError:
            raise ValueError('Feature {} not in {}s features.'.format(updated_feature, self))

        self._update()
    
    def _update(self):

        # reset geometries
        self._featuregeometries = []

        exterior = self._geometry

        for feature in self._features:
            exterior, tmp_geometry = feature._calculate_geometry(exterior)
            self._featuregeometries.append(tmp_geometry)
    
    def _repr_svg_(self):

        shply_collection = shpl_geom.GeometryCollection([self._geometry, *self._featuregeometries])

        svg = shply_collection._repr_svg_()

        return rework_svg(svg, 1000, 250)

    def exportgeometry(self, refpoint=np.zeros(2)):

        geoms = []

        for feature, geometry in zip(self._features, self._featuregeometries):
            geoms.extend(exportstructure(geometry, feature.material, refpoint))
        
        return geoms

    def __getitem__(self, idx):
        return self._features[idx] # TODO rework


class Layer:
    """Layer of constant thickness representation
    
    Parameters
    ----------
    material :
        Material definition
    thickness : float
        The Layers geometric thickness

    Attributes
    ----------
    interior :
        shapely geometry representation of interior
    
    """

    def __init__(self, material, thickness=0.0):
        self.material = material
        self.thickness = thickness

    def _calculate_geometry(self, exterior):

        inside_direction = _get_inside_direction(exterior)

        interior = exterior.parallel_offset(self.thickness, side=inside_direction)

        if interior.type == 'MultiLineString':
            interior = shpl_geom.LinearRing(interior.geoms[0])
        else:
            interior = shpl_geom.LinearRing(interior)

        geometry = shpl_geom.Polygon(exterior)-shpl_geom.Polygon(interior)

        return interior, geometry

    def _centerline(self):

        inside_direction = _get_inside_direction(self.exterior)

        centerline = self.exterior.parallel_offset(self._thickness/2.0,
                                                    side=inside_direction)
        
        return centerline

    def middle_circumference(self):
        """Calculate circumference of centerline
        
        Returns
        -------
        float
            circumference value
        """

        return self._centerline().length

    def enclosed_area(self):
        """Calculate area enclosed by centerline

        Returns
        -------
        float
            ecnlosed area
        """
        
        cline = self._centerline()

        return shpl_geom.Polygon(cline).area


class CompositeLayer(Layer):
    pass #TODO: implement


class Reinforcement(Layer):
    """Local reinforcement structure
    
    Parameters
    ----------
    material :
        Material Defintion
    thickness :
        reinforcement thickness
    limits :
        bounds for reinforcement in chordwise direction

    Attributes
    ----------
    interior :
        shapely geometry representation of interior

    """

    def __init__(self, material, thickness=0.0, limits=None):
        super().__init__(material, thickness)
        self._limits = np.array(limits)
    
    def _calculate_geometry(self, exterior):
        
        limited_box = shpl_geom.box(self._limits[0], exterior.bounds[1]*1.1,
                                    self._limits[1], exterior.bounds[3]*1.1)

        intersection = limited_box.intersection(exterior)

        side = _get_inside_direction(exterior)

        tmp_geometries = []

        tmp_interior = shpl_geom.Polygon(exterior)

        for ageo in intersection.geoms:
            tmp_geometry = _create_offset_box(ageo, self.thickness, side, 
                                              symmetric=False)
            tmp_interior -= tmp_geometry
            tmp_geometries.append(tmp_geometry)

        geometry = shpl_geom.GeometryCollection(tmp_geometries)

        interior = shpl_geom.LinearRing(tmp_interior.exterior)
        
        return _refine_interior(interior), geometry

    def exportgeometry(self, refpoint=np.zeros(2)):

        return [geom2array(geo, refpoint)._replace(material=self.material) for geo in self.geometry.geoms]

class ISpar(_AbstractBaseStructure):
    """Representation for I or double-T Spar
    
    Parameters
    ----------
    material :
        Material defintion.
    midpos : float
        Chord position of spar (absolute)
    flangewidth : float
        width of flanges
    flangethickness : float
        thickness of flanges (symmetric)
    webpos : float
        position of web at flange (relative, 0 - left, 1 - right)
    webthickness : float
        thickness of wepropertyb


    Attributes
    ----------
    interior : 
        shapely geometry representation of interior
    
    Raises
    ------
    Exception
        when geometry cannot be created with choosen parameters

    """

    def __init__(self, material, midpos: float, flangewidth: float,
                 flangethickness: float, webpos: float, webthickness: float):
        super().__init__(material)
        self._midpos = midpos
        self._flangewidth = flangewidth
        self._flangethickness = flangethickness
        self._webpos = webpos
        self._webthickness = webthickness

    @property
    def midpos(self):
        return self._midpos

    @midpos.setter
    def midpos(self,midposnew):
        self._midpos = midposnew
        self._trigger_update()

    @property
    def flangewidth(self):
        return self._flangewidth

    @flangewidth.setter
    def flangewidth(self, newflangewidth):
        self._flangewidth = newflangewidth
        self._trigger_update()

    @property
    def flangethickness(self):
        return self._flangethickness

    @flangethickness.setter
    def flangethickness(self, newflangethickness):
        self._flangethickness = newflangethickness
        self._trigger_update()

    @property
    def webpos(self):
        return self._webpos

    @webpos.setter
    def webpos(self, newwebpos):
        self._webpos = newwebpos
        self._trigger_update()

    @property
    def webthickness(self):
        return self._webthickness

    @webthickness.setter
    def webthickness(self, newwebthickness):
        self._webthickness = newwebthickness
        self._trigger_update()

    def webpos_abs(self):
        return self.midpos + (self.webpos - 0.5) * self.flangewidth

    def _update_geometry(self, exterior):
        self.interior = exterior
        start = self.midpos - self.flangewidth/2
        end = self.midpos + self.flangewidth/2

        if start<exterior.bounds[0] or end > exterior.bounds[2]:
            raise Exception('flange width is too large')

        cutbox = shpl_geom.box(start, exterior.bounds[1]-3,
                               end, exterior.bounds[3]+3)

        cutgeom = cutbox.intersection(exterior)

        offsetside = self._get_inside_direction(exterior)

        flangegeoms = []
        offsetlines = []

        for cutline in cutgeom.geoms:
            flangegeoms.append(
                self._create_offset_box(cutline, self.flangethickness,
                                        offsetside)
            )
            offsetline = cutline.parallel_offset(self.flangethickness,
                                                 side=offsetside)
            offsetlines.append(offsetline)

        webpos_abs = start + self.webpos * self.flangewidth

        line1 = offsetlines[0]
        line2 = offsetlines[1]
        xdist1 = abs(line1.coords[0][0]-line2.coords[-1][0])
        xdist2 = abs(line1.coords[0][0]-line2.coords[0][0])

        if xdist1 < xdist2:
            webbox = shpl_geom.LinearRing([*line2.coords, *line1.coords])
        else:
            webbox = shpl_geom.LinearRing([*line1.coords[::-1], *line2.coords])

        webstart = webpos_abs - self.webthickness/2
        webend = webpos_abs + self.webthickness/2

        webcutbox = shpl_geom.box(webstart, exterior.bounds[1]-3,
                             webend,  exterior.bounds[1]+3)

        web = webcutbox.intersection(shpl_geom.Polygon(webbox))

        self.geometry = shpl_geom.GeometryCollection([*flangegeoms, web])

        self._cut_elements = [cutgeom]

    @property
    def massproperties(self):
        if type(self.material) is dict:
            try:
                webmaterial = self.material['web']
                flangematerial = self.material['flange']
            except:
                raise Exception('wrong material defintion')

            mass = 0.0
            cg = np.zeros(2)

            for ii, geom in enumerate(self.geometry.geoms):
                if ii < 2:
                    material = flangematerial
                else:
                    material = webmaterial
                
                tmpmass = geom.area*material.ρ 
                mass += tmpmass
                cg += np.array(geom.centroid) * tmpmass

            cg /= mass

            return shpl_geom.Point(cg), mass
        else:
            return super().massproperties


class BoxSpar(_AbstractBaseStructure):
    """Representation for box spar
    
    Parameters
    ----------
    material :
        Material defintion.
    midpos : float
        Chord position of spar (absolute)
    width : float
        width of spar
    flangeheight : float
        thickness of flanges (symmetric)
    webwidth : float
        thickness of web


    Attributes
    ----------
    interior : 
        shapely geometry representation of interior

    """

    def __init__(self, material, midpos: float, width: float,
                 flangeheigt, webwidth):
        super().__init__(material)
        self._midpos = midpos
        self._width = width
        self._flangeheigt = flangeheigt
        self._webwidth = webwidth

        self.interior = None

    @property
    def midpos(self):
        return self._midpos

    @midpos.setter
    def midpos(self, newmidpos):
        self._midpos = newmidpos
        self._trigger_update()

    @property
    def width(self):
        return self._width
    
    @width.setter
    def width(self, newwidth):
        self._width = newwidth
        self._trigger_update()

    @property
    def flangeheight(self):
        return self._flangeheigt

    @flangeheight.setter
    def flangeheight(self, newflangeheight):
        self._flangeheigt = newflangeheight
        self._trigger_update()

    @property
    def webwidth(self):
        return self._webwidth

    @webwidth.setter
    def webwidth(self, newwebwidth):
        self._webwidth = newwebwidth
        self._trigger_update()

    def _update_geometry(self, exterior):
        self.interior = exterior
        start = self._midpos-self._width/2
        end = self._midpos+self._width/2

        abox = shpl_geom.box(start, exterior.bounds[1]-3, end, exterior.bounds[3]+3)

        intersection = abox.intersection(shpl_geom.Polygon(exterior))

        # intersection of cut elements with spar forbidden
        #for elem in self._cut_elements:
        #    if not intersection.intersects(elem):
        #        continue
        #    raise Exception('Cannot use cut element in cut element')

        anotherbox = shpl_geom.box(start+self._webwidth,
                              exterior.bounds[1]-3,
                              end-self._webwidth,
                              exterior.bounds[3]+3)

        web = intersection-anotherbox
        flangebox = intersection.intersection(anotherbox)

        flangcutout = shpl_geom.box(start, flangebox.bounds[1]+self._flangeheigt,
                               end, flangebox.bounds[3]-self._flangeheigt)

        flange = flangebox-flangcutout

        self.geometry = shpl_geom.GeometryCollection([*web.geoms, *flange.geoms])

        #self._cut_elements = [abox]

    @property
    def massproperties(self):
        if type(self.material) is dict:
            try:
                webmaterial = self.material['web']
                flangematerial = self.material['flange']
            except:
                raise Exception('wrong material defintion')

            mass = 0.0
            cg = np.zeros(2)

            for ii, geom in enumerate(self.geometry.geoms):
                if ii < 2:
                    material = webmaterial
                else:
                    material = flangematerial
                
                tmpmass = geom.area*material.ρ 
                mass += tmpmass
                cg += np.array(geom.centroid) * tmpmass
            mass = (self.geometry.geoms[0].area+self.geometry.geoms[1].area)*webmaterial.ρ \
                    + (self.geometry.geoms[2].area+self.geometry.geoms[3].area)*flangematerial.ρ 
            cg /= mass

            return shpl_geom.Point(cg), mass
        else:
            return super().massproperties


class MassAnalysis:
    """Analyse Mass of Structure
    
    Parameters
    ----------
    sectionbase
        section definiton to be analyzed
    
    """

    def __init__(self, sectionbase):
        self.secbase = sectionbase

    @property
    def massproperties(self):
        mass = 0.0
        cg = np.zeros(2)
            
        for feature in self.secbase.features:
            cur_cg, cur_mass = feature.massproperties

            mass += cur_mass
            cg += cur_mass * np.array(cur_cg)
        
        return cg/mass, mass


def _oderside(side):
    if side == 'left':
        return 'right'
    else:
        return 'left'


def rework_svg(svg:str, width:float, height:float=100.0, stroke_width:float=None)->str:
    """Prettify svgs generated by shapely
    
    Parameters
    ----------
    svg : str
        svg definitiom
    width : float
        with of returned svg
    height : int, optional
        height of returned svg (the default is 100)
    stroke_width : float, optional
        width of lines in svg (the default is None, which [default_description])
    
    Raises
    ------
    Exception
        raised when input svg string is invalid
    
    Returns
    -------
    str
        prettified svg string
    """

    import re
    
    if stroke_width is None:
        
        search_res = re.search(r'viewBox="((?:-?\d+.\d+\s*){4})"', svg)
        
        if search_res is None:
            raise Exception('Invalid SVG!')
            
        bounds = [float(val) for val in search_res.groups()[0].split()]
        Δy = bounds[3]-bounds[1]
        Δx = bounds[2]-bounds[0]
        
        stroke_width = min(Δx,Δy)/100
    
    svg = re.sub(r'width="\d+\.\d+"',
                 'width="{:.1f}"'.format(width),
                 svg,
                 count=1)
    
    svg = re.sub(r'height="\d+\.\d+"',
                 'heigth="{:.1f}"'.format(height),
                 svg,
                 count=1)
    
    svg = re.sub(r'stroke-width="\d+\.\d+"',
                 'stroke-width="{:f}"'.format(stroke_width),
                 svg)

    return svg


Structure = namedtuple('Structure', ['exterior','interiors','material'])


def exportstructure(geometry, material, refpoint=np.zeros(2)):
    """Helper function to export polygon geometry from shapely to numpy arrays based format
    
    Parameters
    ----------
    geometry : shapely.Polygon
        Geometrie to be exported (must be a Polygon)
    refpoint : np.array, optional
        reference point (2D), will be substracted from coordinates 
        (the default is np.zeros(2)
    
    Raises
    ------
    ValueError
        Wrong geometry type given..
    
    Returns
    -------
    ArrayStruc
        Custom geometry and material container
    """

    def coordsclockwise(linearring):
        if cga.signed_area(linearring) < 0.0:
            return np.array(linearring.coords)
        else:
            return np.array(linearring.coords)[::-1]

    if geometry.type in ('GeometryCollection', 'MultiPolygon'):
        res = []

        for geo in geometry.geoms:
            res.extend(exportstructure(geo, material, refpoint))
        
        return res

    elif geometry.type != 'Polygon':
        raise ValueError('Geometry must be of type \'Polygon\' or \'GeometryCollection\', not {}'.format(geometry.type))

    exterior = coordsclockwise(geometry.exterior) - refpoint.flat

    interiors = [coordsclockwise(interior) - refpoint.flat for interior in geometry.interiors]

    return [Structure(exterior, interiors, material)]
    