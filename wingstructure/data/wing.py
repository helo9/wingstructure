from collections import namedtuple

import numpy as np


class _Wing:
    """A data structue for multi trapez wing definitions.

    Not inteded for usage. Have a look at the Wing class.
    """
    _Section = namedtuple('Section', ['chord', 'airfoil', 'x', 'y', 'z', 'twist'])

    def __init__(self, x=0.0, y=0.0, z=0.0, symmetric=True):
        self.pos = (x, y, z)
        self.symmetric = symmetric
        self.sections = []
    
    def append(self, chord, airfoil='', x=0.0, y=0.0, z=0.0, twist=0.0):
        self.sections.append(
            self._Section(chord, airfoil, x, y, z, twist)
        )

    def get_mac(self):
        """Calculate mean aerodynamic chord.
        
        Returns
        -------
        pos: arraylike
           leading edge position of mean aerodynamic chord
        mac: float
           mac length
        
        Notes
        -----
        Implements formulas reported in http://dx.doi.org/10.1063/1.4951901
        """
        
        pos = np.zeros(3)
        area = 0.0
        mac = 0.0

        lastsec = None

        for sec in self.sections:
            if lastsec is None:
                lastsec = sec
                continue
            
            # short aliases for usage in formulas
            x1, x2 = lastsec.x, sec.x
            y1, y2 = lastsec.y, sec.y
            c1, c2 = lastsec.chord, sec.chord

            # segment properties
            S = (c1+c2)/2 * (y2-y1)
            λ = c2 / c1

            segmac = 2/3 * c1 * (λ**2 + λ + 1) / (λ + 1)         
            segx = x1 + (x2-x1) * (1+2*λ)/(3+3*λ)
            segy = y1 + (y2-y1) * (1+2*λ)/(3+3*λ)

            # sum up values weighted by segment area
            pos += np.array([segx, segy, 0]) * S
            mac += segmac * S

            area += S

            lastsec = sec
        
        pos /= area
        mac /= area

        return pos, mac

    @property
    def span(self):
        """Get span of wing."""
        if self.symmetric:
            return 2*max((sec.y for sec in self.sections))

    @property
    def area(self):
        """Get wing area."""

        span_positions = [sec.y for sec in self.sections]
        chord_lengths = [sec.chord for sec in self.sections]

        area = np.trapz(chord_lengths, span_positions)

        return 2*area if self.symmetric else area

    @property
    def aspectratio(self):
        """Get aspect ratio."""
        return self.span**2/self.area
    
    @property
    def mac(self):
        """Get mac length"""
        return self.get_mac()[1] 


class Wing(_Wing):
    """A object representing lift generating airplane parts.
    
    Parameters
    ----------
    x, y, z: float
       coordinate system offset
    symmetric: bool
       wing symmetry regarding y=0.0
    """

    _ControlSurface = namedtuple('ControlSurface', 
            ['pos1', 'pos2', 'depth1', 'depth2', 'cstype'])

    def __init__(self, x=0.0, y=0.0, z=0.0, symmetric=True):
        super().__init__(x, y, z, symmetric)
        self.controlsurfaces = {}

    def add_controlsurface(self, name, pos1, pos2, depth1, depth2, cstype):
        self.controlsurfaces[name] = self._ControlSurface(
                pos1, pos2, depth1, depth2, cstype)
