import pytest
import numpy as np

# helper functions 

def isclose(a, b, tol=1e-5, rtol=1e-5):
    diff = abs(a-b)
    maxab = max((abs(a), abs(b)))

    return diff<tol and (diff/maxab)<rtol

# fixtures 

@pytest.fixture
def d38wing():
    from wingstructure.data.wing import Wing

    awing = Wing()

    awing.append(chord=0.943, airfoil='FX 61-184')
    awing.append(chord=0.754, airfoil='FX 61-184', pos=(0.0, 4.51, 0.0))
    awing.append(chord=0.377, airfoil='FX 60-12', pos=(0.134, 7.5, 0.0))
    
    return awing


@pytest.fixture
def d43wing():
    from wingstructure.data.wing import Wing

    awing = Wing()

    awing.append((0,0,0), 1.12)
    awing.append((-68e-3,4.0,0.21996), 1.028)
    awing.append((51e-3,7.223,0.42874), 0.673)
    awing.append((0.1753225, 8.5, 0.6328), 0.454537)
    awing.append((0.245, 9.0, 0.7424), 0.36)
    
    return awing

# tests


def test_wingbasicprops(d38wing):
    assert isclose(d38wing.area, 11.03516)
    assert d38wing.span==15.0
    assert isclose(d38wing.aspectratio, 20.3893736)
    # compare mac results with getmac
    macpos, maclength = d38wing.get_mac()
    assert isclose(maclength, 0.7706271)
    assert isclose(macpos[0], 0.2109074-0.7706271/4)


def test_controlsurfaces(d38wing):
    d38wing.add_controlsurface('aileron1', 4.51, 7.125, 0.2, 0.2, 'aileron')


def test_flatten(d43wing):
    flatwing = d43wing.flatten()

    # check new spanwidth
    assert isclose(flatwing.span, 2*9.0408708357794)
    # area should have increased
    assert flatwing.area > d43wing.area
    # mac should decrease
    assert flatwing.mac < d43wing.mac
