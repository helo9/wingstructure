import numpy as np


def calc_lineloadresultants(ys, q):
    """Calculate resultants of loads for piecewise linear load distributin
    
    Parameters
    ----------
    ys : numpy array, list
        grid points
    q : numpy array, list
        field values
    
    Returns
    -------
    array
        discrete resultant forces and coordinates [[x, y, z, Q_x, Q_y, Q_z], ...]
    """

    # calculate element lengths
    Δys = np.diff(ys)
    
    # initialize arrays for
    
    # force resultants
    Q = []
    
    # resultants attack point
    y_res = []

    # segments force resultant acts on
    segs = []
    
    # iterate over parts of wing
    for i in range(1,len(ys)):
        
        if q[i]==0 and q[i-1]==0:
            # Nothing to do..
            continue
        elif (q[i]>=0 and q[i-1]>=0) or (q[i]<=0 and q[i-1]<=0):
            # trapez rule to get resultant
            Q.append(Δys[i-1] * (q[i]+q[i-1])/2)
            # center of trapez as attack point of resultant
            y_res.append(ys[i-1] + np.abs(Δys[i-1])/3 * np.abs((q[i-1]+2*q[i]) / (q[i]+q[i-1])))
            segs.append(i-1)
        else:
            # sign changes from q[i-1] to q[i]
            # cannot be captured by single resultant within this section
            # -> resultants of the two triangles are used
            y_0 = ys[i-1] + Δys[i-1] * np.abs(q[i]/q[i-1]) / (1 + np.abs(q[i]/q[i-1]))

            print(f'y_0 = {y_0, Δys, ys[i-1]}')

            # left triangle
            Q.append(0.5*(y_0-ys[i-1])*q[i-1])
            y_res.append(ys[i-1] + (y_0 - ys[i-1])/3.0)
            segs.append(i-1)

            # right triangle
            Q.append(0.5*(ys[i] - y_0)*q[i])
            y_res.append(ys[i] - (ys[i]-y_0)/3.0)
            segs.append(i-1)
    
    loads = np.zeros((len(y_res), 7))
    loads[:, 1] = y_res
    loads[:, -2] = Q
    loads[:, -1] = segs
    
    return loads


def get_nodes(wing, ys):
    pass


def solve_equilibrium(nodes, loads, free_node):
    """Solves static equilibrium in unbranched stick model
    
    Parameters
    ----------
    nodes : array
        coordinates of nodes: [[x, y, z], ...]
    forces : array
        forces with point of attack and segment: [[x, y, z, fx, fy, fz, seg], ...]
    free_node : int
        designate node without loads
    
    Returns
    -------
    array
        internal loads at nodes [[Qx, Qy Qz, Mx, My, Mz], ...]
    """
    n = len(nodes)
    A = np.zeros([6*n,6*n])
    b = np.zeros(6*n)

    # equilibrium conditions (-x_0 + x_1 = 0)
    for i in range(6*(n-1)):
        A[i][i] = -1
        A[i][i+6] = 1

    # moments resulting from internal forces
    for i in range(n-1):
        lx, ly, lz = nodes[i+1] - nodes[i]
        idx = 6*i

        ## cross product lever x internal force
        A[idx+3][idx+7] = -lz
        A[idx+3][idx+8] = ly

        A[idx+4][idx+6] = lz
        A[idx+4][idx+8] = -lx

        A[idx+5][idx+7] = lx
        A[idx+5][idx+6] = -ly

    # force or moment free boundary conditions
    for i in range(6):
        idx = 6*free_node
        A[6*(n-1) + i][6*free_node + i] = 1

    # right hand side / external forces
    for i in range(n-1):
        for l in loads[loads[:,-1] == i]:
            # force
            b[6*i:6*i+3] += l[3:-1]

            # resulting moment (cross product)
            M = np.cross(l[:3] - nodes[i], l[3:-1]) 
            b[6*i+3:6*i+6] += M

    x = np.linalg.solve(A, -b)

    return np.reshape(x, (len(x)//6, 6))
