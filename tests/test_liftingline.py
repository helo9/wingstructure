import numpy as np
from wingstructure.liftingline import multhopp

def test_multhopp_schlichting():
    Λ = 6 # aspect ratio of wing
    
    b = 15 # m span width
    cs = [b/Λ]*2 # depth of wing
    ys = [0,b/2] # section positions

    αs = [1]*2 # angle of attack
    dcls = [2*np.pi]*2

    # reference result
    ηs_ref = [0,0.3827,0.7071,0.9239,1]
    γs_ref = [0.4320,0.4192,0.3710,0.2485,0]

    # coarse calculation
    M = 7

    res = multhopp(αs, cs, ys, dcls, M = M, mode='gamma')

    assert np.isclose(res[0][M//2:]/b*2, ηs_ref[:-1], atol=1e-4).all()
    assert np.isclose(res[1][M//2:], γs_ref[:-1], atol=1e-4).all()