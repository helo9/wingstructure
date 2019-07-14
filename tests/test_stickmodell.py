import pytest
import numpy as np


def test_lineloadresultants():
    from wingstructure.structure.stickmodel import calc_lineloadresultants

    loads = calc_lineloadresultants((-2.0, -1.0, 1.0, 2.0, 3.0, 4.0, 5.0), (1.0, 1.0, -1.0, 1.0, 2.0, 0.0, 0.0))

    # check that all not involved values are zero
    assert (loads[:,0]==0.0).all()
    assert (loads[:,2]==0.0).all()
    assert (loads[:,3]==0.0).all()
    assert (loads[:,4]==0.0).all()

    # check positions of resulting forces
    assert np.isclose(loads[:,1], (-1.5, -2/3, 2/3, 1+1/6, 2-1/6, 2+5/9, 3+1/3)).all()

    # check values of resulting forces
    assert np.isclose(loads[:,5], (1, 0.5, -0.5, -0.25, 0.25, 1.5, 1)).all()

    # check segment assigment
    assert np.all(loads[:,-1] == [0, 1, 1, 2, 2 ,3, 4])


def test_solve2Ds():
    from wingstructure.structure.stickmodel import solve_equilibrium

    nodes = np.array([[0,0,0], [0,1,0], [0,2,0]])
    loads = np.array([
        [0, 0.5, 0, 0, 1, 1, 0],
        [0, 1.5, 0, 0, 0, 2, 1]
    ])

    free_node = 2

    sol = solve_equilibrium(nodes, loads, free_node)

    assert np.isclose(sol, [
        [0, 1, 3, 3.5, 0, 0],
        [0, 0, 2, 1, 0, 0],
        [0, 0, 0, 0, 0, 0]
    ]).all()
