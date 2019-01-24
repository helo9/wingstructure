import numpy as np

# TODO: Warning all outlines have to be clockwise defined


def calcarea(outline):
    
    x_i, y_i = outline.T
    x_ip1, y_ip1 = np.roll(outline.T, 1, axis=1)
    
    A = 0.5 * np.sum(y_ip1*x_i-y_i*x_ip1)
    
    return A


def calcstaticmoments(outline):
    
    x_i, y_i = outline.T
    x_ip1, y_ip1 = np.roll(outline.T, 1, axis=1)
    
    S_x = 1/6 * np.sum((y_i+y_ip1)*(y_ip1*x_i-y_i*x_ip1))
    S_y = 1/6 * np.sum((x_i+x_ip1)*(y_ip1*x_i-y_i*x_ip1))
    
    return S_x, S_y


def calcinertiamoments(outline):
    
    x_i, y_i = outline.T
    x_ip1, y_ip1 = np.roll(outline.T, 1, axis=1)
    
    I_xx = 1/12 * np.sum((y_ip1**2 + (y_i+y_ip1)*y_i)\
                         *(y_ip1*x_i-y_i*x_ip1))
    I_yy = 1/12 * np.sum((x_ip1**2 + (x_i+x_ip1)*x_i)\
                         *(y_ip1*x_i-y_i*x_ip1))
    I_xy = 1/12 * np.sum(0.5*x_ip1**2*y_i**2-0.5*x_i**2*y_ip1**2\
                          -(y_ip1*x_i-y_i*x_ip1)*(x_i*y_i+x_ip1*y_ip1))
    
    return I_xx, I_yy, I_xy


def calcneutralcenter(outline):
    
    area_ = calcarea(outline)
    
    S_x, S_y = calcstaticmoments(outline)
    
    x_nc = S_y/area_
    y_nc = S_x/area_
    
    return x_nc, y_nc


def calcprincipalaxis(I_xx, I_yy, I_xy):
    return np.arctan2(2*I_xy, I_yy-I_xx)


def transform_intertiamoments(I_xx, I_yy, I_xy, φ):
    I_ξξ = (I_xx+I_yy)/2 + (I_yy-I_xx)/2 * np.cos(2*φ) - I_xy * np.sin(2*φ)
    I_ηη = (I_xx+I_yy)/2 - (I_yy-I_xx)/2 * np.cos(2*φ) + I_xy * np.sin(2*φ)
    I_ξη = (I_yy-I_xx)/2 * np.cos(2*φ) + I_xy * np.sin(2*φ)

    return I_ξξ, I_ηη, I_ξη


def calcgeom(geom, property_functions):

    properties = {propfun:None for propfun in property_functions}

    isexterior = True
    for outline in (geom.exterior, *geom.interiors):
        if isexterior:
            for propfun in property_functions:
                properties[propfun] = np.array(propfun(outline))
            isexterior = False
        else:
            for propfun in property_functions:
                properties[propfun] -= np.array(propfun(outline))

    return [properties[propfun] for propfun in property_functions]


# TODO implement AnalaysisClass
# TODO: allow secbase and feature as input
class StructuralAnalysis:
    def __init__(self, structure):
        self._structure = structure
        self.nc = None
        self.staticmoments = None
        self.intertiamoments = None

    def update(self):
        # calculate normal center

        self.area = 0

        weighted_area_ = 0
        weighted_staticmoment_ = np.zeros((2))

        for geom in self._structure.exportgeometry():
            area, staticmoment = calcgeom(geom, [calcarea, calcstaticmoments])

            self.area += area
            weighted_area_ += geom.material.E*area
            weighted_staticmoment_ += geom.material.E*staticmoment

        self.nc = weighted_staticmoment_/weighted_area_        

        #TODO: calculate properties regarding normal center

        self.bendingstiffness = np.zeros(3)

        for geom in self._structure.exportgeometry(self.nc):
            inertiamoment = calcgeom(geom, [calcinertiamoments])[0]

            self.bendingstiffness += inertiamoment*geom.material.E
