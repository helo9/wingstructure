import numpy as np


def calc_lineloadresultants(ys, q):
    """
    Calculate resultants of line loads for segments
    """
    # calculate element lengths
    Δys = np.diff(ys)
    
    # initialize arrays for
    
    # force resultants
    Q = []
    
    # resultants attack point
    y_res = []
    
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
        else:
            # sign changes from q[i-1] to q[i]
            # cannot be captured by single resultant within this section
            # -> resultants of the two triangles are used
            y_0 = ys[i-1] + Δys[i-1] * np.abs(q[i]/q[i-1]) / (1 + np.abs(q[i]/q[i-1]))

            print(f'y_0 = {y_0, Δys, ys[i-1]}')

            # left triangle
            Q.append(0.5*(y_0-ys[i-1])*q[i-1])
            y_res.append(ys[i-1] + (y_0 - ys[i-1])/3.0)

            # right triangle
            Q.append(0.5*(ys[i] - y_0)*q[i])
            y_res.append(ys[i] - (ys[i]-y_0)/3.0)
    
    loads = np.zeros((len(y_res), 6))
    loads[:, 1] = y_res
    loads[:, -1] = Q

    custom_types = np.dtype({
    'names': ['x', 'y', 'z', 'Q_x', 'N', 'Q_z'],
    'formats': ['f4',]*6
         })
    
    return np.array([tuple(a) for a in loads], dtype=custom_types)


def combine_loads( loadslist ):
    loads = np.vstack(loadslist)
    
    # sort by y coord
    loads = loads[np.flip(loads[:,1].argsort())]
    
    return loads


def calc_moments(coords, discrete_loads):
    """Calculates cummulated forces and moments
    """
    
    # number of grid points
    n = coords.shape[0]
    
    # initialize arrays with zeros for cumulated forces and moments
    Q_k = np.zeros((n, 3))
    M = np.zeros_like(Q_k)

    # no discrete loads -> return zeros
    if discrete_loads.shape[0] == 0:
        return Q_k, M

    # split up loads
    coords_Qs = discrete_loads[:,:3]
    Qs = discrete_loads[:,3:]
    
    # iterate over grid points
    j = 0
    for i in range(1, n):

        # initialize cumulated force with previous one
        Q_k[i,:] += Q_k[i-1,:]

        # initialize section moment with
        # previous sections moment + moment of previous cumulated force
        a = (coords[i-1] - coords[i]).T
        M[i,:] += M[i-1,:] + np.cross(Q_k[i-1, :], a)

        while np.abs(coords_Qs[j, 1]) > np.abs(coords[i, 1]):
            # sum up forces
            Q_k[i,:] += Qs[j,:]

            # sum up resulting moments
            ## lever
            a = (coords_Qs[j, :] - coords[i, :]).T

            ## cross product for moment
            M[i,:] += np.cross(Qs[j,:],a)

            j += 1

            # break if j exceeds resultants size
            if j >= Qs.shape[0]: break
    
    return Q_k, M