import numpy as np
from sympy import *

nodes = np.array([[0,0,0], [0,1,0], [0,2,0]])
loads = [[np.array([0,.5,0,0,0,1])],[np.array([0,1.5,0,0,0,1])]]
free_node = 1

def solve_equilibrium(nodes, loads, free_node):
    n = len(nodes)
    A = np.zeros([6*n,6*n])
    b = np.zeros(6*n)

    ## Gleichgewicht (-x_0 + x_1 = 0)
    for i in range(6*(n-1)):
        A[i][i] = 1
        A[i][i+6] = -1

    ## Querkraftmoment
    for i in range(n-1):
        lx, ly, lz = nodes[i+1] - nodes[i]
        idx = 6*i

        ## Kreuzprodukt l x Q
        A[idx+3][idx+7] = lz
        A[idx+3][idx+8] = -ly

        A[idx+4][idx+6] = -lz
        A[idx+4][idx+8] = lx

        A[idx+5][idx+7] = -lx
        A[idx+5][idx+6] = ly

    ## Randbedingungen (knoten ist frei, also keine kraft)
    for i in range(6):
        idx = 6*free_node
        A[6*(n-1) + i][6*free_node + i] = 1

    #for i in range(6*free_node, 6*(free_node+1)):
    #    A[i][i] = 1

    ## Rechte Seite
    for i in range(n-1):
        for l in loads[i]:
            b[6*i:6*i+3] += l[3:] # Kraft
            M = np.cross(l[:3] - nodes[i], l[3:])
            b[6*i+3:6*i+6] += M

    print(A)
    x = np.linalg.solve(A, b)
    return x

solve_equilibrium(nodes, loads, free_node)
