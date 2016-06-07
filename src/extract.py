#*********************************************************************************
#* Copyright (C) 2016 Kosuke Sato, Alexey V. Akimov
#*
#* This file is distributed under the terms of the GNU General Public License
#* as published by the Free Software Foundation, either version 2 of
#* the License, or (at your option) any later version.
#* See the file LICENSE in the root directory of this distribution
#* or <http://www.gnu.org/licenses/>.
#*
#*********************************************************************************/

## \file extract.py
# This module implements the functions that extract
# atomic forces , molecular energies, molecular orbitals, and atomic basis information
# written in gamess output file.

import os
import sys
import math

if sys.platform=="cygwin":
    from cyglibra_core import *
elif sys.platform=="linux" or sys.platform=="linux2":
    from liblibra_core import *

import detect
import ao_basis


def extract_ao_basis(inp_str, label, R, flag):
    ##
    # Finds the keywords and their patterns and extracts the parameters
    # \param[in] l_gam : The list which contains the lines of the (GAMESS output) file.
    # \param[in] params : The list which contains extracted data from l_gam file.
    # This function returns the atomic orbital basis as "expo_" and "coef_" of param.
    #
    # Used in: extract.py/extract

    # atomic species
    l_atom_spec = []
    atom_spec = []
    sz = len(inp_str)

    for i in xrange(sz):
        spline = inp_str[i].split()
        if len(spline) == 1:
            l_atom_spec.append(i)
            # atom labels
            atom = spline[0]
            if len(atom) > 1:
                atom = atom[0] + atom[1].lower()
            atom_spec.append(atom)


    # atomic basis sets
    basis_type = []
    basis_expo = []
    basis_coef = []

    for i in range(0,len(atom_spec)):
        stmp = atom_spec[i]
        type_tmp = []
        expo_tmp = []
        coef_tmp = []
        if i < len(atom_spec) - 1:
            tmp_start = l_atom_spec[i] + 2
            tmp_end = l_atom_spec[i+1] - 2
        else:
            tmp_start = l_atom_spec[i] + 2
            tmp_end = sz - 1 #ab_end

        for j in range(tmp_start,tmp_end+1):
            spline = inp_str[j].split()
            coef_tmp1 = []
            if len(spline) > 1:
                type_tmp.append(spline[1])
                expo_tmp.append(float(spline[3]))
                if spline[1] == "L":
                    coef_tmp1.append(float(spline[4]))
                    coef_tmp1.append(float(spline[5]))
                else:
                    coef_tmp1.append(float(spline[4]))
                coef_tmp.append(coef_tmp1)
        basis_type.append(type_tmp)
        basis_expo.append(expo_tmp)
        basis_coef.append(coef_tmp)


    # ******* get the Gaussian primitives parameters *******
    expo_s = []
    expo_p = []
    expo_d = []
    coef_s = []
    coef_p = []
    coef_d = []

    for la in label: # all atoms

        for j in range(0,len(atom_spec)): # specify the kind of the atom
            if la == atom_spec[j]:
                i = j

        expo_stmp = []
        expo_ptmp = []
        expo_dtmp = []

        coef_stmp = []
        coef_ptmp = []
        coef_dtmp = []

        for j in range(0,len(basis_type[i])): # basis number of atoms
            b_tmp = basis_type[i][j]
            if b_tmp == "S":
                expo_stmp.append(basis_expo[i][j])
                coef_stmp.append(basis_coef[i][j][0])
            elif b_tmp == "P":
                expo_ptmp.append(basis_expo[i][j])
                coef_ptmp.append(basis_coef[i][j][0])
            elif b_tmp == "D":
                expo_dtmp.append(basis_expo[i][j])
                coef_dtmp.append(basis_coef[i][j][0])
            elif b_tmp == "L":
                expo_stmp.append(basis_expo[i][j])
                expo_ptmp.append(basis_expo[i][j])
                coef_stmp.append(basis_coef[i][j][0])
                coef_ptmp.append(basis_coef[i][j][1])
            # f orbitals are not taken into account, so should add them.

        expo_s.append(expo_stmp)
        expo_p.append(expo_ptmp)
        expo_d.append(expo_dtmp)
        coef_s.append(coef_stmp)
        coef_p.append(coef_ptmp)
        coef_d.append(coef_dtmp)


    orb_name, scount, pcount, dcount, lcount = ao_basis.input_AO_name(label, atom_spec, basis_type, flag)

    ao_data = {}
    ao_data["expo_s"] = expo_s
    ao_data["expo_p"] = expo_p
    ao_data["expo_d"] = expo_d
    ao_data["coef_s"] = coef_s
    ao_data["coef_p"] = coef_p
    ao_data["coef_d"] = coef_d

    if flag == 1:
        print "expo_s=",ao_data["expo_s"]
        print "expo_p=",ao_data["expo_p"]
        print "expo_d=",ao_data["expo_d"]
        print "coef_s=",ao_data["coef_s"]
        print "coef_p=",ao_data["coef_p"]
        print "coef_d=",ao_data["coef_d"]


    ao = ao_basis.construct_ao_basis(ao_data,label,R,scount,orb_name)

    return ao


def extract_mo(inp_str,Ngbf,flag):
    ##
    # Extracts MO-LCAO coefficients from the the list of input lines
    # 
    # \param[in] inp_str  Strings containing the info for all orbitals
    # E - returned MATRIX object, containing the eigenvalues
    # C - returned MATRIX object, containing the eigenvectors:
    # C.get(a,i) - is the coefficient of AO with index a in the MO with index i
    #
    # Used in: extract.py/extract

    stat_span = Ngbf + 4 # period for beginning of coefficient lines

    #mol_ene = []
    l_tmp = []
    mol_coef = []
    sz = len(inp_str) 

    # create objects of MATRIX type, containing eigenvalues and eigenvectors 
    E = MATRIX(Ngbf,Ngbf)
    C = MATRIX(Ngbf,Ngbf)

    for i in xrange(sz):

        if i % stat_span == 0 :
            ind_of_eig = inp_str[i].split() # split lines for indexes of eigenvalues

            # eigenvalues
            eig_val = inp_str[i+1].split() # split lines for eigenvalues
            for j in range(0,len(ind_of_eig)):
                k = int(ind_of_eig[j]) - 1           # python index start from 0
                E.set(k,k,float(eig_val[j]))

            # molecular coefficients
            ic = i + 3                              # beginning of coefficient lines
            for j in range(ic,ic+Ngbf):             # loop for AO basis
                eig_vec = inp_str[j].split()        # split lines for eigenvectors
                for k in range(0,len(ind_of_eig)):  
                    ja = int(eig_vec[0]) - 1            # index of AO basis
                    ke = int(ind_of_eig[k]) - 1         # index of eigenvectors
                    if len(eig_vec[1]) == 4:        # continuous word like "CL44"
                        kvec = k + 3
                    else:                           # discontinuous word like "H 20" 
                        kvec = k + 4
                    C.set(ja,ke,float(eig_vec[kvec]))

    if flag == 1:
        #print "E Matrix is"; E.show_matrix()
        #print "C Matrix is"; C.show_matrix()
        print "E(0,0) is",E.get(0,0)
        print "E(Ngbf-1,Ngbf-1) is",E.get(Ngbf-1,Ngbf-1)
        print "C(0,0) is",C.get(0,0) 
        print "C(Ngbf-1,0) is",C.get(Ngbf-1,0)
        print "C(0,Ngbf-1) is",C.get(0,Ngbf-1)
        print "C(Ngbf-1,Ngbf-1) is",C.get(Ngbf-1,Ngbf-1)

    return E, C
    

def extract_coordinates(inp_str,flag):
    ##
    # Extracts atomic labels, nuclear charges, and coordinates of all atoms
    # from the the list of input lines
    # each input line is assumed to have the format:
    # label  Q  ....  x y z

    # \param[in] inp_str  Strings containing the info for all atoms
    # label - returned list of atomic labels (strings)
    # Q - returned list of nuclear charges (floats)
    # R - returned list of nuclear coordinates (VECTOR objects)

    #
    # Used in: extract.py/extract


    label, Q, R = [], [], []
    for a in inp_str: 
        spline = a.split() 

        # atom labels
        atom = spline[0]
        if len(atom) > 1:
            atom = atom[0] + atom[1].lower()
        label.append(atom)

        # atomic charges
        Q.append(float(spline[1]))

        # coordinates of atoms: Last 3 elements of the line
        x = float(spline[len(spline)-3])
        y = float(spline[len(spline)-2])
        z = float(spline[len(spline)-1])
        r = VECTOR(x,y,z)
        R.append(r)

    if flag == 1:
        print "label=", label
        print "charges=", Q
        print "coor_atoms="
        for r in R:
            print R.index(r), r, r.x, r.y, r.z


    return label, Q, R


def extract_gradient(inp_str,flag):
    ##
    # Extracts atomic gradients on all atoms from the the list of input lines
    # each input line is assumed to have the format:
    #  ....  gx  gy  gz
    #
    # \param[in] inp_str  Strings containing the gradient for all atoms
    # grad - returned list of VECTOR objects
    #
    # Used in: extract.py/extract

    grad = []
    for a in inp_str:
        spline = a.split()  

        # Last 3 elements of the line
        x = float(spline[len(spline)-3])
        y = float(spline[len(spline)-2])
        z = float(spline[len(spline)-1])
        g = VECTOR(x,y,z)

        grad.append(g)

    if flag == 1:
        print "atomic gradient="
        for g in grad:
            print grad.index(g), g, g.x, g.y, g.z

    return grad


def extract(filename,flag_deb,flag_ao):
    ##
    # Finds the keywords and their patterns and extracts the parameters
    # \param[in] filename : The list which contains the lines of the (GAMESS output) file.
    # \param[in] flag_deb     : a flag for debugging detect module
    # \param[in] flag_ao      : a flag for using atomic oribital basis 
    # This function returns the coordinates of atoms, gradients, atomic orbital basis,
    # and molecular orbitals extracted from the file, in the form of dictionary
    #
    # Used in: gamess_to_libra.py/gamess_to_libra and main.py/main

    f = open(filename,"r")
    A = f.readlines()
    f.close()

    # detect the lines including information from gamess output file
    info = detect.detect(A,flag_deb,flag_ao)

    # extract information from gamess output file
    label, Q, R = extract_coordinates(A[info["coor_start"]:info["coor_end"]+1], flag_deb)
    grad = extract_gradient(A[info["grad_start"]:info["grad_end"]+1], flag_deb)
    E, C = extract_mo(A[info["mo_start"]:info["mo_end"]+1], info["Ngbf"], flag_deb)

    ao = []
    if flag_ao == 1:
        ao = extract_ao_basis(A[info["ab_start"]:info["ab_end"]+1], label, R, flag_deb)

    
    if flag_deb == 1:
        print "********************************************"
        print "extract program ends"
        print "********************************************\n"

    return label, Q, R, grad, E, C, ao, info["tot_ene"]


