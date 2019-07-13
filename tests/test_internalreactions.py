import pytest
import numpy as np


def test_lineloadresultants():
    from wingstructure.structure.internalreactions import calc_lineloadresultants

    loads = calc_lineloadresultants((-2.0, -1.0, 1.0, 2.0, 3.0, 4.0, 5.0), (1.0, 1.0, -1.0, 1.0, 2.0, 0.0, 0.0))

    # check that all not involved values are zero
    assert (loads['x']==0.0).all()
    assert (loads['z']==0.0).all()
    assert (loads['N']==0.0).all()
    assert (loads['Q_x']==0.0).all()

    # check positions of resulting forces
    assert np.isclose(loads['y'], (-1.5, -2/3, 2/3, 1+1/6, 2-1/6, 2+5/9, 3+1/3)).all()

    # check size of resulting forces
    assert np.isclose(loads['Q_z'], (1, 0.5, -0.5, -0.25, 0.25, 1.5, 1)).all()