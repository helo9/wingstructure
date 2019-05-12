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
           
        """
        
        pos = np.zeros(3)
        area = 0.0
        mac = 0.0

        lastsec = None

        for sec in self.sections:
            if lastsec is None:
                lastsec = sec
                continue
            
            # calculate segment properties
            segspan = sec.y - lastsec.y
            segarea = (sec.chord + lastsec.chord) * segspan / 2
            taper = sec.chord / lastsec.chord
            taper1 = 1 + taper
            frac = (taper + taper1) / (3 * taper1)

            segmac = lastsec.chord * (taper**2 + taper1) / (1.5*taper1)
            segx = lastsec.x + frac * (sec.x - lastsec.x)
            segy = lastsec.y + frac * segspan

            # sum up values weighted by segment area
            pos += np.array([segx, segy, 0]) * segarea
            mac += segmac * segarea

            area += segarea

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
