
 ***** CORRECT ***** (VERSION Apr 16, 2026  BUILT=20260616)   5-Sep-2026

 INPUT PARAMETER VALUES
 ----------------------
 SPACE_GROUP_NUMBER=    1 as used in the INTEGRATE step
 UNIT_CELL_CONSTANTS=    77.274    77.377   161.089  89.936  90.095 101.085 as used by INTEGRATE
 FRIEDEL'S_LAW=TRUE 
 PROFILE_FITTING= TRUE 
 OVERLOAD=     29991     MINPK=  75.00000    WFAC1=   1.0
 INCLUDE_RESOLUTION_RANGE=    20.000     0.000
 NAME_TEMPLATE_OF_DATA_FRAMES=/data/xtal_1/xtal_1_??????.h5
 DATA_RANGE=       1    1800
 ROTATION_AXIS=  0.999973 -0.000142  0.007360
 OSCILLATION_RANGE=  0.200000
 STARTING_ANGLE=     5.885     STARTING_FRAME=       1
 X-RAY_WAVELENGTH=  0.979338
 INCIDENT_BEAM_DIRECTION= -0.002591 -0.001718  0.999995
 FRACTION_OF_POLARIZATION=   0.990
 POLARIZATION_PLANE_NORMAL=  0.000000  1.000000  0.000000
 AIR=   0.00032
 DETECTOR=EIGER
 SILICON=  3.705086 SENSOR_THICKNESS=  0.450000
 NUMBER OF DETECTOR SEGMENTS   1
 NX=  4150  NY=  4371    QX=  0.075000  QY=  0.075000
 ORGX=   2008.90  ORGY=   2253.10
 DETECTOR_DISTANCE=   197.440
 DIRECTION_OF_DETECTOR_X-AXIS=   1.00000   0.00000   0.00000
 DIRECTION_OF_DETECTOR_Y-AXIS=   0.00000   1.00000   0.00000
 BEAM_DIVERGENCE_E.S.D.=   0.035
 REFLECTING_RANGE_E.S.D.=   0.135
 MINIMUM_ZETA=     0.050
 MAXIMUM_ERROR_OF_SPOT_POSITION=   3.0
 MAXIMUM_ERROR_OF_SPINDLE_POSITION=   2.0
 MINIMUM_I/SIGMA=   1.0
 REFLECTIONS/CORRECTION_FACTOR=    5000
 SNRC=  0.10 I/sigma for use in scaling factor determination
 STRICT_ABSORPTION_CORRECTION=FALSE 
 CORRECTIONS= DECAY MODULATION ABSORPTION                      
 TEST_RESOLUTION_RANGE=    10.000     5.000     MIN_RFL_Rmeas=    50     MAX_FAC_Rmeas=    2.00
 REFERENCE_DATA_SET=                                                  
 FIT_B-FACTOR_TO_REFERENCE_DATA_SET=FALSE 

 2437155 REFLECTIONS ON FILE "INTEGRATE.HKL"
       0 CORRUPTED REFLECTION RECORDS (IGNORED)
       0 MATCHING REFLECTIONS SPECIFIED IN FILE "FILTER.HKL"
       0 REFLECTIONS INCOMPLETE OR OUTSIDE IMAGE RANGE       1 ...    1800
       0 OVERLOADED REFLECTIONS (IGNORED)
     362 REFLECTIONS OUTSIDE ACCEPTED RESOLUTION RANGES
                OR TOO CLOSE TO ROTATION AXIS (IGNORED)
 2436793 REFLECTIONS ACCEPTED



 ******************************************************************************
                      AUTOMATIC SPACE GROUP ASSIGNMENT
 ******************************************************************************

 XDS adopts the following approach.
 (1) it looks for possible symmetries of the crystal lattice
 (2) it computes a redundancy independent R-factor for all enantiomorphous
     point groups compatible with the observed lattice symmetry.
 (3) it selects the group which explains the intensity data at an acceptable,
     redundancy-independent R-factor (Rmeas, Rrim) using a minimum number of
     unique reflections.

 This approach does not test for the presence of screw axes. Consequently,
 orthorhombic cell axes will be specified in increasing length (following
 conventions), despite the possibility that different assignments for the
 cell axes could become necessary for space groups P222(1) and P2(1)2(1)2
 containing one or two screw axes, respectively.

 The user can always override the automatic decisions by specifying the
 correct space group number and unit cell constants in XDS.INP and repeating
 the CORRECT step of XDS. This provides a simple way to rename orthorhombic
 cell constants if screw axes are present.

 In addition, the user has the option to specify in XDS.INP
 (a) a reference data set or
 (b) a reindexing transformation or
 (c) the three basis vectors (if known from processing a previous data set
 taken at the same crystal orientation in a multi-wavelength experiment).
 These features of XDS are useful for resolving the issue of alternative
 settings of polar or rhombohedral cells (like P4, P6, R3).

 =====> Specifications provided by the user in XDS.INP:
 SPACE_GROUP_NUMBER=   20 (0: unknown symmetry and unit cell)
 UNIT_CELL_CONSTANTS=    99.00   120.00   161.00  90.000  90.000  90.000
 UNIT_CELL_A-AXIS=     0.000     0.000     0.000 (0 0 0 : unknown)
 UNIT_CELL_B-AXIS=     0.000     0.000     0.000 (0 0 0 : unknown)
 UNIT_CELL_C-AXIS=     0.000     0.000     0.000 (0 0 0 : unknown)
 REIDX=  0  0  0  0  0  0  0  0  0  0  0  0 (all 0 : not specified)
 TEST_RESOLUTION_RANGE=   10.00    5.00 (Angstrom) for space group determination
 NUMBER OF ACCEPTED REFLECTIONS FOR CALCULATING Rmeas            51590
 NUMBER OF ACCEPTED UNIQUE REFLECTIONS FROM REFERENCE DATA SET       0


 *********** DETERMINATION OF LATTICE CHARACTER AND BRAVAIS LATTICE ***********

 The CHARACTER OF A LATTICE is defined by the metrical parameters of its
 reduced cell as described in the INTERNATIONAL TABLES FOR CRYSTALLOGRAPHY
 Volume A, p. 746 (KLUWER ACADEMIC PUBLISHERS, DORDRECHT/BOSTON/LONDON, 1989).
 Note that more than one lattice character may have the same BRAVAIS LATTICE.

 A lattice character is marked "*" to indicate a lattice consistent with the
 observed locations of the diffraction spots. These marked lattices must have
 low values for the QUALITY OF FIT and their implicated UNIT CELL CONSTANTS
 should not violate the ideal values by more than
 MAX_CELL_AXIS_ERROR=  0.03
 MAX_CELL_ANGLE_ERROR=           2.0 (Degrees)

 The REINDEXING TRANSFORMATION REIDX() consists of 12 integers that relate
 the original indices H,K,L from file INTEGRATE.HKL to the indices H',K',L'
 with respect to the new cell.
    H'=(REIDX(1)*H+REIDX( 2)*K+REIDX( 3)*L)/IDXV+REIDX( 4)
    K'=(REIDX(5)*H+REIDX( 6)*K+REIDX( 7)*L)/IDXV+REIDX( 8)
    L'=(REIDX(9)*H+REIDX(10)*K+REIDX(11)*L)/IDXV+REIDX(12)
 The value of the integer IDXV depends on the lattice type used for
 specifying reflections on file INTEGRATE.HKL; IDXV is
 1 for a primitive,
 2 for a face or body centred,
 3 for a rhombohedral,
 4 for a lattice centred on all faces.
 IDXV is set by XDS and cannot be input by the user.

  LATTICE-  BRAVAIS-   QUALITY  UNIT CELL CONSTANTS (ANGSTROEM & DEGREES)    REINDEXING TRANSFORMATION
 CHARACTER  LATTICE     OF FIT      a      b      c   alpha  beta gamma

 *  31        aP          0.0      77.3   77.4  161.1  89.9  89.9  78.9    1  0  0  0  0 -1  0  0  0  0 -1  0
 *  44        aP          1.2      77.3   77.4  161.1  89.9  90.1 101.1    1  0  0  0  0  1  0  0  0  0  1  0
 *  10        mC          1.9     119.4   98.3  161.1  90.0  90.1  90.1    1 -1  0  0  1  1  0  0  0  0  1  0
 *  34        mP          4.1      77.3  161.1   77.4  89.9 101.1  90.1   -1  0  0  0  0  0 -1  0  0 -1  0  0
 *  13        oC          5.4      98.3  119.4  161.1  89.9  90.0  89.9    1  1  0  0 -1  1  0  0  0  0  1  0
 *  14        mC          5.4      98.3  119.4  161.1  89.9  90.0  89.9    1  1  0  0 -1  1  0  0  0  0  1  0
    33        mP         98.6      77.3   77.4  161.1  89.9  90.1 101.1    1  0  0  0  0  1  0  0  0  0  1  0
    35        mP         99.2      77.4   77.3  161.1  90.1  89.9 101.1    0 -1  0  0 -1  0  0  0  0  0 -1  0
    32        oP        100.3      77.3   77.4  161.1  89.9  90.1 101.1    1  0  0  0  0  1  0  0  0  0  1  0
    11        tP        101.7      77.3   77.4  161.1  89.9  90.1 101.1    1  0  0  0  0  1  0  0  0  0  1  0
    29        mC        154.0      77.3  159.1  161.1  90.0  90.1  72.6    1  0  0  0  1  2  0  0  0  0  1  0
    39        mC        156.6     159.1   77.3  161.1  90.1  90.0  72.6   -1 -2  0  0 -1  0  0  0  0  0 -1  0
    38        oC        157.8      77.3  159.1  161.1  90.0  90.1 107.4   -1  0  0  0  1  2  0  0  0  0 -1  0
    12        hP        159.1      77.3   77.4  161.1  89.9  90.1 101.1    1  0  0  0  0  1  0  0  0  0  1  0
    28        mC        295.2      77.3  331.2   77.4  92.5 101.1  76.6   -1  0  0  0 -1  0 -2  0  0 -1  0  0
    30        mC        295.9      77.4  331.3   77.3  92.5 101.1  76.6    0 -1  0  0  0 -1  2  0 -1  0  0  0
    37        mC        345.7     331.2   77.3   77.4 101.1  92.5  76.6    1  0  2  0  1  0  0  0  0  1  0  0
    36        oC        346.9      77.3  331.2   77.4  87.5 101.1 103.4    1  0  0  0 -1  0 -2  0  0  1  0  0
    41        mC        347.0     331.2   77.3   77.4 101.1  92.5  76.6    1  0  2  0  1  0  0  0  0  1  0  0
    40        oC        348.2      77.3  331.2   77.4  87.5 101.1 103.4    1  0  0  0 -1  0 -2  0  0  1  0  0
    27        mC        495.9     159.1   77.3  178.6  85.3 112.4  72.6   -1 -2  0  0 -1  0  0  0  0  1 -1  0
    42        oI        597.5      77.3   77.4  336.8 100.8 100.6 101.1   -1  0  0  0  0 -1  0  0  1  1  2  0
    15        tI        598.2      77.3   77.4  336.8  79.2  79.4 101.1    1  0  0  0  0  1  0  0  1  1  2  0
    26        oF        619.8      77.3  159.1  331.2  86.0 103.4 107.4    1  0  0  0 -1 -2  0  0 -1  0 -2  0
     9        hR        746.1      77.3   98.3  497.6  90.0 100.6 129.4    1  0  0  0 -1 -1  0  0 -1  1 -3  0
     1        cF        999.0     188.7  200.3  188.7 133.2  62.8 133.3    1  1 -1  0  1 -1  1  0 -1 -1 -1  0
     2        hR        999.0      98.3  178.5  200.7 121.7  90.0 105.9    1  1  0  0 -1  0 -1  0 -1  1  1  0
     3        cP        999.0      77.3   77.4  161.1  89.9  90.1 101.1    1  0  0  0  0  1  0  0  0  0  1  0
     5        cI        999.0     178.5   98.3  178.8  74.0  39.0  74.1    1  0  1  0  1  1  0  0  0  1  1  0
     4        hR        999.0     119.4  178.8  188.7 128.8  89.9 109.6    1 -1  0  0 -1  0  1  0 -1 -1 -1  0
     6        tI        999.0     178.8  178.5   98.3  74.1  74.0  39.0    0  1  1  0  1  0  1  0  1  1  0  0
     7        tI        999.0     178.5   98.3  178.8  74.0  39.0  74.1    1  0  1  0  1  1  0  0  0  1  1  0
     8        oI        999.0      98.3  178.5  178.8  39.0  74.0  74.1   -1 -1  0  0 -1  0 -1  0  0 -1 -1  0
    16        oF        999.0      98.3  119.4  336.8  90.1 106.9  89.9   -1 -1  0  0  1 -1  0  0  1  1  2  0
    17        mC        999.0     119.4   98.3  178.5  74.1 109.4  89.9    1 -1  0  0 -1 -1  0  0 -1  0 -1  0
    18        tI        999.0     178.6  188.7   77.3  70.8  94.7 128.7    0  1 -1  0  1  1  1  0  1  0  0  0
    19        oI        999.0      77.3  178.6  188.7  51.3  70.8  85.3   -1  0  0  0  0  1 -1  0 -1 -1 -1  0
    20        mC        999.0     178.8  178.6   77.3  94.7  94.9 128.7    0 -1 -1  0  0 -1  1  0 -1  0  0  0
    21        tP        999.0      77.4  161.1   77.3  90.1 101.1  89.9    0  1  0  0  0  0  1  0  1  0  0  0
    22        hP        999.0      77.4  161.1   77.3  89.9 101.1  90.1    0 -1  0  0  0  0  1  0 -1  0  0  0
    23        oC        999.0     178.8  178.6   77.3  85.3  94.9  51.3    0  1  1  0  0 -1  1  0  1  0  0  0
    24        hR        999.0     226.5  178.6   77.3  85.3  78.0  68.1    1  2  1  0  0 -1  1  0  1  0  0  0
    25        mC        999.0     178.8  178.6   77.3  85.3  94.9  51.3    0  1  1  0  0 -1  1  0  1  0  0  0
    43        mI        999.0      98.3  336.8   77.3 100.6 129.4  73.1   -1 -1  0  0 -1 -1 -2  0  1  0  0  0

 ****** LATTICE SYMMETRY IMPLICATED BY SPACE GROUP SYMMETRY ******

BRAVAIS-            POSSIBLE SPACE-GROUPS FOR PROTEIN CRYSTALS
  TYPE                     [SPACE GROUP NUMBER,SYMBOL]
  aP      [1,P1]
  mP      [3,P2] [4,P2(1)]
 mC,mI    [5,C2]
  oP      [16,P222] [17,P222(1)] [18,P2(1)2(1)2] [19,P2(1)2(1)2(1)]
  oC      [21,C222] [20,C222(1)]
  oF      [22,F222]
  oI      [23,I222] [24,I2(1)2(1)2(1)]
  tP      [75,P4] [76,P4(1)] [77,P4(2)] [78,P4(3)] [89,P422] [90,P42(1)2]
          [91,P4(1)22] [92,P4(1)2(1)2] [93,P4(2)22] [94,P4(2)2(1)2]
          [95,P4(3)22] [96,P4(3)2(1)2]
  tI      [79,I4] [80,I4(1)] [97,I422] [98,I4(1)22]
  hP      [143,P3] [144,P3(1)] [145,P3(2)] [149,P312] [150,P321] [151,P3(1)12]
          [152,P3(1)21] [153,P3(2)12] [154,P3(2)21] [168,P6] [169,P6(1)]
          [170,P6(5)] [171,P6(2)] [172,P6(4)] [173,P6(3)] [177,P622]
          [178,P6(1)22] [179,P6(5)22] [180,P6(2)22] [181,P6(4)22] [182,P6(3)22]
  hR      [146,R3] [155,R32]
  cP      [195,P23] [198,P2(1)3] [207,P432] [208,P4(2)32] [212,P4(3)32]
          [213,P4(1)32]
  cF      [196,F23] [209,F432] [210,F4(1)32]
  cI      [197,I23] [199,I2(1)3] [211,I432] [214,I4(1)32]


 Several solutions exist for the given space group that explain the data. The
 selected solution (marked "*") correlates best with the given reference data set.
 The independent settings of the cell can be obtained by application of the
 REINDEXING TRANSFORMATION to the original indices H,K,L from file INTEGRATE.HKL

 CORRELATION = correlation factor with the reference data set
 NPAIR       = number of unique reflection pairs correlated 
 Rmeas=Rrim  = redundancy independent R-factor (intensities)
               For definition see:
               Rmeas : Diederichs & Karplus,
                       Nature Struct. Biol. 4, 269-275 (1997);
               Rrim  : Weiss & Hilgenfeld,
                       J.Appl.Cryst. 30,203-205 (1997).
 COMPARED    = number of reflections used for calculating Rmeas
 ESD         = Agreement with given unit cell geometry

 CORRELATION  NPAIR  Rmeas  COMPARED  ESD       REINDEX TRANSFORMATION

  *   0.00        0    9.9   47829    0.01 -1 -1  0  0 -1  1  0  0  0  0 -1  0

 ************ SELECTED SPACE GROUP AND UNIT CELL FOR THIS DATA SET ************

 SPACE_GROUP_NUMBER=   20
 UNIT_CELL_CONSTANTS=    99.00   120.00   161.00  90.000  90.000  90.000
 UNIT_CELL_A-AXIS=    59.549    77.438    10.798
 UNIT_CELL_B-AXIS=   -90.031    62.401    47.520
 UNIT_CELL_C-AXIS=    41.440   -52.394   146.585
 REFLECTIONS H,K,L FROM "INTEGRATE.HKL" WILL BE REINDEXED BY
 H' = ( -1*H + -1*K +  0*L)/ 1 +  0
 K' = ( -1*H +  1*K +  0*L)/ 1 +  0
 L' = (  0*H +  0*K + -1*L)/ 1 +  0

 *****  8 EQUIVALENT POSITIONS IN SPACE GROUP # 20 *****

    If x',y',z' is an equivalent position to x,y,z, then
        x'=x*ML(1)+y*ML( 2)+z*ML( 3)+ML( 4)/12.0
        y'=x*ML(5)+y*ML( 6)+z*ML( 7)+ML( 8)/12.0
        z'=x*ML(9)+y*ML(10)+z*ML(11)+ML(12)/12.0

    #    1  2  3  4    5  6  7  8    9 10 11 12 
    1    1  0  0  0    0  1  0  0    0  0  1  0
    2    1  0  0  0    0 -1  0  0    0  0 -1  0
    3   -1  0  0  0    0 -1  0  0    0  0  1  6
    4   -1  0  0  0    0  1  0  0    0  0 -1  6
    5    1  0  0  6    0  1  0  6    0  0  1  0
    6    1  0  0  6    0 -1  0  6    0  0 -1  0
    7   -1  0  0  6    0 -1  0  6    0  0  1  6
    8   -1  0  0  6    0  1  0  6    0  0 -1  6

 ******************************************************************************
      MEAN DISCREPANCIES BETWEEN OBSERVED AND CALCULATED SPOT LOCATIONS
 ******************************************************************************

 The discrepancies in X- and Y-coordinates of the spots are depicted in the
 two images DX-CORRECTIONS.cbf and DY-CORRECTIONS.cbf for inspection with
 the XDS-Viewer.



 ******************************************************************************
  REFINEMENT OF DIFFRACTION PARAMETERS USING ALL IMAGES
 ******************************************************************************


 REFINED VALUES OF DIFFRACTION PARAMETERS DERIVED FROM    535816 INDEXED SPOTS
 REFINED PARAMETERS:   POSITION BEAM AXIS ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     1.30
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.10
 SPACE GROUP NUMBER     20
 UNIT CELL PARAMETERS     98.558   119.657   161.545  90.000  90.000  90.000
 E.S.D. OF CELL PARAMETERS  5.7E-02 1.1E-01 9.4E-02 0.0E+00 0.0E+00 0.0E+00
 REC. CELL PARAMETERS   0.010146  0.008357  0.006190  90.000  90.000  90.000
 COORDINATES OF UNIT CELL A-AXIS    59.677    77.684    10.842
 COORDINATES OF UNIT CELL B-AXIS   -90.130    62.575    47.736
 COORDINATES OF UNIT CELL C-AXIS    41.503   -52.409   147.063
 CRYSTAL MOSAICITY (DEGREES)     0.135
 LAB COORDINATES OF ROTATION AXIS  0.999974 -0.000017  0.007161
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.001428 -0.000955  1.021097
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    2001.93   2248.48
 DETECTOR ORIGIN (PIXELS) AT                     2005.63   2250.95
 CRYSTAL TO DETECTOR DISTANCE (mm)       198.10
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000


 THE DATA COLLECTION STATISTICS REPORTED BELOW ASSUMES:
 SPACE_GROUP_NUMBER=   20
 UNIT_CELL_CONSTANTS=    98.56   119.66   161.55  90.000  90.000  90.000


 ******************************************************************************
        MEAN INTENSITY AS FUNCTION OF SPINDLE POSITION WITHIN DATA IMAGE
 ******************************************************************************

 This statistics could serve as a diagnostic tool for detecting
 shutter problems (suggested by Kay Diederichs).
 Data are corrected for this effect if PATCH_SHUTTER_PROBLEM=TRUE in XDS.INP.
 ===> Selected : PATCH_SHUTTER_PROBLEM=FALSE

 INTERVAL = Angular interval in units of the oscillation range
            covered by a data image.
 NUMBER   = Number of reflections in each interval
 INTENSITY= Mean intensity of the reflections in each interval
 FACTOR   = Correction factor applied to intensities;
            INTENSITY(overall)/INTENSITY(interval)

   INTERVAL     NUMBER      INTENSITY      FACTOR
 -0.05  0.05    243806         28.184       1.005
  0.05  0.15    244128         28.631       0.990
  0.15  0.25    243526         28.299       1.001
  0.25  0.35    242941         28.246       1.003
  0.35  0.45    243918         28.480       0.995
  0.45  0.55    243819         28.372       0.999
  0.55  0.65    242646         28.025       1.011
  0.65  0.75    243151         28.329       1.000
  0.75  0.85    244453         28.168       1.006
  0.85  0.95    244405         28.650       0.989

 -0.05  0.95   2436793         28.339       1.000


 ******************************************************************************
           CORRECTION FACTORS AS FUNCTION OF IMAGE NUMBER & RESOLUTION
 ******************************************************************************

 RECIPROCAL CORRECTION FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     

 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW= TRUE
 TOTAL NUMBER OF CORRECTION FACTORS DEFINED      289
 DEGREES OF FREEDOM OF CHI^2 FIT           1313177.9
 CHI^2-VALUE OF FIT OF CORRECTION FACTORS      0.713
 NUMBER OF CYCLES CARRIED OUT                      3

 CORRECTION FACTORS for visual inspection by XDS-Viewer DECAY.cbf           
 XMIN=     0.3 XMAX=  1799.6 NXBIN=   17
 YMIN= 0.00251 YMAX= 0.53078 NYBIN=   17
 NUMBER OF REFLECTIONS USED FOR DETERMINING CORRECTION FACTORS    1510050


 ******************************************************************************
  CORRECTION FACTORS AS FUNCTION OF X (fast) & Y(slow) IN THE DETECTOR PLANE
 ******************************************************************************

 RECIPROCAL CORRECTION FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     

 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW= TRUE
 TOTAL NUMBER OF CORRECTION FACTORS DEFINED      306
 DEGREES OF FREEDOM OF CHI^2 FIT           1313169.6
 CHI^2-VALUE OF FIT OF CORRECTION FACTORS      0.708
 NUMBER OF CYCLES CARRIED OUT                      6

 CORRECTION FACTORS for visual inspection by XDS-Viewer MODPIX.cbf          
 XMIN=     6.0 XMAX=  4143.1 NXBIN=   17
 YMIN=     5.8 YMAX=  4363.3 NYBIN=   18
 NUMBER OF REFLECTIONS USED FOR DETERMINING CORRECTION FACTORS    1510050


 ******************************************************************************
   CORRECTION FACTORS AS FUNCTION OF IMAGE NUMBER & DETECTOR SURFACE POSITION
 ******************************************************************************

 RECIPROCAL CORRECTION FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     

 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW= TRUE
 TOTAL NUMBER OF CORRECTION FACTORS DEFINED      221
 DEGREES OF FREEDOM OF CHI^2 FIT           1313173.9
 CHI^2-VALUE OF FIT OF CORRECTION FACTORS      0.701
 NUMBER OF CYCLES CARRIED OUT                      3

 CORRECTION FACTORS for visual inspection by XDS-Viewer ABSORP.cbf          
 XMIN=     0.3 XMAX=  1799.6 NXBIN=   17
 DETECTOR_SURFACE_POSITION=    2075    2185
 DETECTOR_SURFACE_POSITION=    2777    2925
 DETECTOR_SURFACE_POSITION=    1372    2925
 DETECTOR_SURFACE_POSITION=    1372    1444
 DETECTOR_SURFACE_POSITION=    2777    1444
 DETECTOR_SURFACE_POSITION=    3665    2878
 DETECTOR_SURFACE_POSITION=    2733    3859
 DETECTOR_SURFACE_POSITION=    1416    3859
 DETECTOR_SURFACE_POSITION=     484    2878
 DETECTOR_SURFACE_POSITION=     484    1491
 DETECTOR_SURFACE_POSITION=    1416     510
 DETECTOR_SURFACE_POSITION=    2733     510
 DETECTOR_SURFACE_POSITION=    3665    1491
 NUMBER OF REFLECTIONS USED FOR DETERMINING CORRECTION FACTORS    1510050


 ******************************************************************************
    CORRECTION PARAMETERS FOR THE STANDARD ERROR OF REFLECTION INTENSITIES
 ******************************************************************************

 The variance v0(I) of the intensity I obtained from counting statistics is
 replaced by v(I)=a*(v0(I)+b*I^2). The model parameters a, b are chosen to
 minimize the discrepancies between v(I) and the variance estimated from
 sample statistics of symmetry related reflections. This model implicates
 an asymptotic limit ISa=1/SQRT(a*b) for the highest I/Sigma(I) that the
 experimental setup can produce (Diederichs (2010) Acta Cryst D66, 733-740).

     a        b          ISa
 7.950E-01  2.797E-03   21.21


 ******************************************************************************
      STANDARD ERROR OF REFLECTION INTENSITIES AS FUNCTION OF RESOLUTION
      FOR DATA SET  XDS_ASCII.HKL                                     
 ******************************************************************************

  I/Sigma  = mean intensity/Sigma of a reflection in shell
  Chi^2    = goodness of fit between sample variances of
             symmetry-related intensities and their errors
             (Chi^2 = 1 for perfect agreement)
  R-FACTOR
  observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
  expected = expected R-FACTOR derived from Sigma(I)

   NUMBER  = number of reflections in resolution shell
             used for calculation of R-FACTOR
  ACCEPTED = number of accepted reflections
  REJECTED = number of rejected reflections (MISFITS),
             recognized by comparison with symmetry-related
             reflections.

 RESOLUTION RANGE  I/Sigma  Chi^2  R-FACTOR  R-FACTOR  NUMBER ACCEPTED REJECTED
                                   observed  expected

   19.948  11.326    19.61   1.21      3.43      3.65    3803    3803     293
   11.326   8.744    19.30   1.11      3.41      3.71    5817    5817     263
    8.744   7.380    17.87   1.20      3.66      3.82    7379    7379     338
    7.380   6.503    16.77   1.23      3.92      3.98    8353    8353     338
    6.503   5.880    16.15   1.30      4.28      4.10    9650    9650     344
    5.880   5.407    16.26   1.26      4.12      4.03   10157   10157     444
    5.407   5.032    16.33   1.33      4.22      4.03    9630    9630     474
    5.032   4.726    16.67   1.32      4.04      3.97   11040   11040     609
    4.726   4.470    16.97   1.30      4.01      3.94   11860   11860     593
    4.470   4.251    16.63   1.39      4.25      3.99   11792   11792     832
    4.251   4.061    15.92   1.45      4.54      4.10   11530   11530     834
    4.061   3.895    14.24   1.44      4.88      4.36   13067   13067     811
    3.895   3.748    13.93   1.48      5.20      4.50   14125   14125     855
    3.748   3.616    13.47   1.48      5.49      4.65   14896   14896     875
    3.616   3.497    12.61   1.48      5.88      4.89   15431   15431     743
    3.497   3.390    11.68   1.48      6.32      5.22   16122   16122     735
    3.390   3.291    10.66   1.45      7.08      5.78   17276   17276     688
    3.291   3.201     9.85   1.43      7.53      6.16   17278   17278     634
    3.201   3.118     9.35   1.38      8.03      6.66   18416   18416     542
    3.118   3.041     7.96   1.34      9.26      7.81   18965   18965     450
    3.041   2.969     7.28   1.28     10.12      8.75   19680   19680     304
    2.969   2.902     6.81   1.25     10.80      9.45   19914   19914     256
    2.902   2.840     5.96   1.21     12.47     11.13   20571   20571     234
    2.840   2.781     5.35   1.19     13.80     12.49   21098   21098     176
    2.781   2.726     4.89   1.14     14.87     13.78   21521   21521     154
    2.726   2.674     4.35   1.11     17.00     15.93   21601   21601     127
    2.674   2.625     3.96   1.11     18.76     17.71   21435   21435     164
    2.625   2.578     3.87   1.09     18.79     17.88   19919   19919     125
    2.578   2.534     3.57   1.08     20.73     19.75   21527   21527     111
    2.534   2.492     3.28   1.09     22.76     21.55   22408   22408     113
    2.492   2.452     3.02   1.05     24.41     23.56   22910   22910      71
    2.452   2.414     2.66   1.03     27.87     27.34   23393   23393      62
    2.414   2.378     2.68   1.04     27.56     26.95   22766   22766      98
    2.378   2.343     2.42   1.00     30.33     30.13   21263   21263      57
    2.343   2.310     2.30   1.01     32.12     31.94   23282   23282      55
    2.310   2.278     2.25   0.98     32.55     32.75   23552   23552      62
    2.278   2.248     1.95   0.99     38.49     38.65   24589   24589      46
    2.248   2.218     1.68   0.97     44.50     44.96   24672   24672      33
    2.218   2.190     1.65   0.96     45.30     46.01   26036   26036      29
    2.190   2.163     1.39   0.95     53.50     54.81   25487   25487      28
    2.163   2.136     1.31   0.93     56.75     58.37   26844   26844       9
    2.136   2.111     1.18   0.95     63.29     64.43   27060   27060      15
    2.111   2.087     1.07   0.95     69.68     71.33   26838   26838      17
    2.087   2.063     0.99   0.93     74.85     77.41   27718   27718      11
    2.063   2.040     0.96   0.91     76.65     79.83   27686   27686      10
    2.040   2.018     0.91   0.92     82.01     85.11   28289   28289      10
    2.018   1.997     0.76   0.92     96.23    100.08   28948   28948      17
    1.997   1.976     0.69   0.92    106.53    110.57   29145   29145      13
    1.976   1.956     0.60   0.89    120.17    126.32   29281   29281       7
    1.956   1.937     0.52   0.90    137.70    144.58   29490   29490       8
    1.937   1.918     0.51   0.90    142.26    149.54   30215   30215      11
    1.918   1.899     0.47   0.90    154.70    162.58   30027   30027       7
    1.899   1.881     0.44   0.89    162.41    171.05   30816   30816       5
    1.881   1.864     0.39   0.88    182.73    193.85   30861   30861       5
    1.864   1.847     0.34   0.88    206.62    218.35   31123   31123       2
    1.847   1.831     0.33   0.88    214.83    227.84   30143   30143       7
    1.831   1.815     0.30   0.89    230.27    242.82   28834   28834      10
    1.815   1.799     0.27   0.87    257.66    274.80   30001   30001       6
    1.799   1.784     0.24   0.86    284.65    305.26   30521   30521      19
    1.784   1.769     0.22   0.87    312.13    332.90   31111   31111      23
    1.769   1.755     0.20   0.85    337.32    364.36   31930   31930       6
    1.755   1.741     0.18   0.86    374.66    400.94   32330   32330       6
    1.741   1.727     0.16   0.86    409.28    439.40   30273   30273       6
    1.727   1.713     0.15   0.85    423.44    454.80   30272   30272       6
    1.713   1.700     0.14   0.85    467.50    503.31   30533   30533       7
    1.700   1.687     0.14   0.86    466.37    499.51   31744   31744       4
    1.687   1.675     0.13   0.85    488.39    526.95   32186   32186       2
    1.675   1.663     0.13   0.86    485.40    519.29   33169   33169       5
    1.663   1.651     0.11   0.85    549.60    593.56   33403   33403       3
    1.651   1.639     0.11   0.86    566.65    608.27   33601   33601       4
    1.639   1.627     0.12   0.85    547.98    589.55   34002   34002       9
    1.627   1.616     0.09   0.86    654.01    700.80   33988   33988       5
    1.616   1.605     0.10   0.86    636.53    683.64   35069   35069       4
    1.605   1.594     0.09   0.86    661.79    707.90   35053   35053       2
    1.594   1.584     0.09   0.85    669.41    721.12   35036   35036       3
    1.584   1.573     0.07   0.84    822.10    886.60   35521   35521       6
    1.573   1.563     0.08   0.85    727.00    783.73   36183   36183       2
    1.563   1.553     0.07   0.84    858.61    931.65   36123   36123      10
    1.553   1.543     0.07   0.85    800.54    860.85   36466   36466       3
    1.543   1.534     0.08   0.84    754.67    816.34   36376   36376       5
    1.534   1.524     0.07   0.84    803.51    870.50   37132   37132       8
    1.524   1.515     0.06   0.84    920.46    995.45   36397   36397      10
    1.515   1.506     0.07   0.86    876.37    940.68   37174   37174       5
    1.506   1.497     0.06   0.84    908.43    986.65   37113   37113      16
    1.497   1.488     0.05   0.85   1004.44   1080.80   37007   37007       7
    1.488   1.480     0.06   0.85    883.48    954.00   36916   36916       6
    1.480   1.471     0.05   0.85   1122.59   1209.91   34327   34327       1
    1.471   1.463     0.04   0.86   1171.84   1254.62   31449   31449       7
    1.463   1.455     0.07   0.85    843.79    911.78   29411   29411       5
    1.455   1.446     0.05   0.85   1020.06   1102.16   27112   27112       6
    1.446   1.439     0.06   0.85    871.10    938.49   24884   24884      10
    1.439   1.431     0.03   0.85   1375.92   1479.32   23272   23272       8
    1.431   1.423     0.05   0.86   1064.01   1141.63   22366   22367       7
    1.423   1.416     0.05   0.84    964.95   1044.00   16139   16157       9
    1.416   1.408     0.05   0.84    924.57   1001.96   11337   11436       6
    1.408   1.401     0.06   0.86    742.24    798.83    9733    9913      12
    1.401   1.394     0.07   0.82    629.13    692.50    7336    7588      22
    1.394   1.386     0.08   0.80    555.61    611.70    4595    5115      19
    1.386   1.379     0.06   0.84    850.55    924.36    2695    3653       8
    1.379   1.373    -0.01   0.74    382.74    457.51     432    1268       2
   --------------------------------------------------------------------------
   19.948   1.373     2.21   0.96     15.22     15.32 2419247 2422111   14484



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR VARIOUS SUBSETS OF INCLUDED DATA IMAGES
 ******************************************************************************

 Data set statistics is reported below several times, each with a different
 upper limit on the number of images included. This provides the user with
 the information for deciding which data images should be excluded from the
 final data set because of radiation damage or other defects. If the user
 decides for a subset of "good" images that differs from the specification
 as given by the input parameter (see DATA_RANGE= in XDS.INP) the CORRECT-
 step of XDS must be repeated with the new parameter values for DATA_RANGE=.


 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1     201
 ******************************************************************************


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       11122    5648      8117       69.6%       2.6%      3.1%     9120   23.49      3.4%    99.8*    17    0.852     370
     2.89       20615   10861     13689       79.3%       4.4%      4.2%    16674   15.03      5.7%    99.6*    -8    0.812     429
     2.37       26912   14380     17480       82.3%      12.2%     11.7%    21995    6.11     16.2%    97.1*     0    0.819     296
     2.05       31458   17507     20544       85.2%      29.4%     30.4%    24830    2.63     39.3%    84.6*    -6    0.711     143
     1.84       36836   20205     23200       87.1%      74.3%     79.2%    29736    0.99     99.7%    43.0*    -5    0.697     152
     1.68       38120   21952     25594       85.8%     194.9%    210.8%    29768    0.35    265.3%     7.8    -14    0.566     125
     1.56       42606   24319     27713       87.8%     383.3%    419.4%    33964    0.16    524.0%     1.6      3    0.609     225
     1.46       44037   25874     29794       86.8%     579.6%    628.6%    34112    0.09    796.8%     1.7     -6    0.537     294
     1.37       17590   13529     31636       42.8%     764.4%    842.9%     7917    0.06   1068.0%     2.1     -6    0.507      56
    total      269296  154275    197767       78.0%      10.3%     10.9%   208116    3.01     13.8%    99.7*    -2    0.721    2090


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES    271603
 NUMBER OF REJECTED MISFITS                              2267
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                    0
 NUMBER OF ACCEPTED OBSERVATIONS                       269336
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 154300



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1     401
 ******************************************************************************


 AVERAGE INTENSITY FOR      85 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     1.0% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       22461    6947      8117       85.6%       3.0%      3.4%    21529   29.88      3.5%    99.8*    15*   0.880    2486
     2.89       41579   12388     13689       90.5%       5.0%      4.7%    39961   19.98      5.9%    99.7*     0    0.893    4731
     2.37       53727   16203     17480       92.7%      13.5%     12.8%    51984    8.28     15.9%    98.1*    -1    0.828    5475
     2.05       62762   19245     20544       93.7%      32.5%     32.9%    60384    3.61     38.2%    90.3*    -2    0.758    5966
     1.84       73560   21940     23200       94.6%      86.5%     91.3%    71154    1.35    101.5%    55.5*     0    0.679    7266
     1.68       76112   24222     25594       94.6%     227.4%    242.7%    73660    0.46    271.1%    11.6*    -2    0.590    6288
     1.56       85185   26209     27713       94.6%     444.6%    476.3%    82512    0.22    526.4%     2.3     -1    0.555    7538
     1.46       87883   28047     29794       94.1%     701.2%    747.1%    85351    0.11    838.5%     0.0      0    0.544    7839
     1.37       35039   20805     31636       65.8%     902.5%    970.3%    24813    0.06   1193.8%     0.9    -14    0.489     373
    total      538308  176006    197767       89.0%      12.1%     12.6%   511348    4.03     14.3%    99.8*     0    0.683   47962


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES    542354
 NUMBER OF REJECTED MISFITS                              3853
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                   85
 NUMBER OF ACCEPTED OBSERVATIONS                       538416
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 176043



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1     601
 ******************************************************************************


 AVERAGE INTENSITY FOR      99 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     0.7% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       33977    7765      8117       95.7%       3.4%      3.6%    33232   34.20      3.9%    99.8*    13*   0.970    3772
     2.89       62541   13474     13689       98.4%       5.7%      5.0%    61516   22.89      6.4%    99.7*     0    0.953    7106
     2.37       80584   17415     17480       99.6%      15.3%     14.3%    79575    9.24     17.2%    98.3*    -2    0.842    9841
     2.05       94246   20486     20544       99.7%      36.9%     37.3%    93002    3.98     41.5%    91.2*    -1    0.768   11858
     1.84      110383   23088     23200       99.5%     100.0%    104.4%   109028    1.46    111.7%    59.0*     0    0.695   14009
     1.68      114222   25379     25594       99.2%     262.4%    278.8%   112869    0.49    295.8%    12.5*     0    0.614   15369
     1.56      127829   27344     27713       98.7%     505.2%    539.3%   126505    0.23    567.0%     2.3     -1    0.562   17642
     1.46      131855   28831     29794       96.8%     781.3%    832.0%   130783    0.12    880.5%    -0.7      0    0.541   18821
     1.37       52036   22053     31636       69.7%     895.1%    957.2%    44343    0.07   1091.9%     0.7     -1    0.524    4741
    total      807673  185835    197767       94.0%      13.4%     13.6%   790853    4.70     15.1%    99.8*     0    0.674  103159


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES    813317
 NUMBER OF REJECTED MISFITS                              5402
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                   99
 NUMBER OF ACCEPTED OBSERVATIONS                       807816
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 185869



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1     801
 ******************************************************************************


 AVERAGE INTENSITY FOR      99 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     0.7% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       45664    8010      8117       98.7%       3.4%      3.7%    45553   39.62      3.7%    99.9*    13*   0.948    6280
     2.89       83738   13687     13689      100.0%       5.8%      5.1%    83699   26.40      6.3%    99.8*    -1    0.932   11898
     2.37      107534   17473     17480      100.0%      16.1%     15.1%   107503   10.46     17.6%    98.7*    -1    0.843   15140
     2.05      125698   20542     20544      100.0%      39.3%     39.6%   125679    4.45     43.0%    93.1*     0    0.778   18370
     1.84      147090   23194     23200      100.0%     106.1%    111.3%   147067    1.61    115.6%    63.8*     0    0.699   21068
     1.68      152305   25577     25594       99.9%     279.5%    299.0%   152211    0.53    306.2%    15.5*     0    0.611   21904
     1.56      170481   27702     27713      100.0%     539.6%    581.1%   170384    0.24    589.4%     2.7     -1    0.561   24650
     1.46      175843   29639     29794       99.5%     791.7%    851.6%   175587    0.13    867.5%    -0.7      0    0.544   25213
     1.37       69015   24026     31636       75.9%     907.0%    980.4%    61774    0.08   1066.6%    -0.4     -1    0.526    6903
    total     1077368  189850    197767       96.0%      13.6%     13.9%  1069457    5.35     14.9%    99.9*     0    0.683  151426


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   1084129
 NUMBER OF REJECTED MISFITS                              6463
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                   99
 NUMBER OF ACCEPTED OBSERVATIONS                      1077567
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 189890



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1    1000
 ******************************************************************************


 AVERAGE INTENSITY FOR      99 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     0.7% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       57240    8032      8117       99.0%       3.5%      3.8%    57221   44.41      3.7%    99.9*    17*   0.996    6802
     2.89      104637   13689     13689      100.0%       5.9%      5.3%   104631   29.46      6.4%    99.8*     2    0.955   12546
     2.37      134227   17480     17480      100.0%      16.6%     15.6%   134221   11.53     17.8%    99.0*     0    0.851   16250
     2.05      156877   20544     20544      100.0%      40.7%     41.1%   156875    4.87     43.6%    94.3*    -1    0.776   19327
     1.84      183682   23198     23200      100.0%     109.1%    114.6%   183682    1.77    116.7%    69.0*     0    0.701   22061
     1.68      190094   25587     25594      100.0%     289.4%    309.6%   190080    0.58    311.1%    17.3*     0    0.615   24113
     1.56      212844   27704     27713      100.0%     556.4%    598.8%   212840    0.26    596.6%     2.9     -1    0.564   26452
     1.46      219539   29786     29794      100.0%     817.3%    881.2%   219522    0.14    879.3%    -0.4      0    0.542   27997
     1.37       86380   26048     31636       82.3%     903.7%    981.1%    80619    0.08   1048.6%     0.7      0    0.529    9288
    total     1345520  192068    197767       97.1%      13.8%     14.2%  1339691    5.89     14.9%    99.9*     0    0.685  164836


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   1353586
 NUMBER OF REJECTED MISFITS                              7715
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                   99
 NUMBER OF ACCEPTED OBSERVATIONS                      1345772
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 192111



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1    1200
 ******************************************************************************


 AVERAGE INTENSITY FOR     140 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     1.5% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       68690    8033      8117       99.0%       3.5%      3.8%    68681   48.71      3.8%    99.9*    17*   1.028    6884
     2.89      125637   13689     13689      100.0%       6.0%      5.3%   125633   32.26      6.4%    99.9*     2    0.954   12582
     2.37      161059   17480     17480      100.0%      16.8%     15.9%   161057   12.58     17.8%    99.1*     0    0.850   16325
     2.05      188163   20544     20544      100.0%      41.3%     41.8%   188162    5.30     43.8%    95.3*    -2    0.772   19402
     1.84      220430   23197     23200      100.0%     111.1%    116.8%   220430    1.92    117.5%    72.4*     0    0.705   22100
     1.68      228037   25587     25594      100.0%     297.3%    317.4%   228024    0.63    315.5%    20.0*     0    0.621   24269
     1.56      255359   27705     27713      100.0%     572.8%    615.3%   255356    0.28    606.6%     4.6     -1    0.564   26551
     1.46      263391   29783     29794      100.0%     845.3%    909.0%   263375    0.16    897.5%    -0.5      0    0.543   28269
     1.37      103905   26326     31636       83.2%     916.8%    993.5%    99056    0.08   1039.1%     1.4     -1    0.523   11643
    total     1614671  192344    197767       97.3%      14.1%     14.5%  1609774    6.43     15.0%    99.9*     0    0.684  168025


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   1624188
 NUMBER OF REJECTED MISFITS                              9045
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  140
 NUMBER OF ACCEPTED OBSERVATIONS                      1615003
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 192389



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1    1400
 ******************************************************************************


 AVERAGE INTENSITY FOR     198 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     1.6% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       79901    8034      8117       99.0%       3.9%      3.9%    79897   52.32      4.1%    99.9*    17*   1.065    6941
     2.89      146388   13689     13689      100.0%       6.4%      5.5%   146384   34.31      6.7%    99.9*     0    0.960   12594
     2.37      187940   17480     17480      100.0%      17.7%     16.7%   187939   13.23     18.6%    99.2*     0    0.857   16368
     2.05      219601   20543     20544      100.0%      43.8%     44.2%   219600    5.54     46.0%    95.6*    -2    0.778   19426
     1.84      257183   23197     23200      100.0%     117.9%    123.4%   257183    2.00    123.6%    74.0*     0    0.708   22111
     1.68      266181   25591     25594      100.0%     314.5%    335.4%   266168    0.64    330.7%    22.2*     0    0.618   24388
     1.56      297979   27704     27713      100.0%     595.8%    638.3%   297976    0.29    625.5%     4.0     -1    0.563   26598
     1.46      307324   29786     29794      100.0%     863.0%    926.3%   307317    0.17    908.0%     0.6      1    0.540   28336
     1.37      121095   26910     31636       85.1%     934.4%   1008.1%   117066    0.09   1044.7%     1.9      0    0.527   12934
    total     1883592  192934    197767       97.6%      14.7%     14.9%  1879530    6.81     15.5%    99.9*     0    0.686  169696


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   1895183
 NUMBER OF REJECTED MISFITS                             11078
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  198
 NUMBER OF ACCEPTED OBSERVATIONS                      1883907
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 192973



 ******************************************************************************
  SUMMARY OF DATA SET STATISTICS FOR IMAGE   DATA_RANGE=       1    1600
 ******************************************************************************


 AVERAGE INTENSITY FOR     198 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     1.6% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04       91163    8034      8117       99.0%       4.0%      3.9%    91162   55.74      4.2%    99.9*    16*   1.088    6957
     2.89      167114   13689     13689      100.0%       6.6%      5.6%   167112   36.18      6.9%    99.9*     1    0.966   12614
     2.37      214905   17480     17480      100.0%      18.5%     17.5%   214905   13.77     19.3%    99.3*     0    0.857   16380
     2.05      251129   20542     20544      100.0%      46.2%     46.7%   251128    5.72     48.2%    95.9*    -2    0.778   19457
     1.84      294044   23197     23200      100.0%     124.4%    130.2%   294044    2.05    129.6%    75.4*    -1    0.706   22119
     1.68      304472   25592     25594      100.0%     331.7%    354.1%   304466    0.65    346.5%    22.0*    -1    0.618   24494
     1.56      340752   27708     27713      100.0%     622.9%    668.9%   340752    0.30    649.9%     5.0     -1    0.561   26632
     1.46      351283   29784     29794      100.0%     885.3%    952.6%   351276    0.17    925.4%    -0.1      0    0.540   28375
     1.37      138506   27333     31636       86.4%     951.4%   1027.3%   135150    0.09   1051.8%     1.7      0    0.531   13858
    total     2153368  193359    197767       97.8%      15.1%     15.2%  2149995    7.14     15.8%    99.9*     0    0.686  170886


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   2167029
 NUMBER OF REJECTED MISFITS                             13154
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  198
 NUMBER OF ACCEPTED OBSERVATIONS                      2153677
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 193390



 ******************************************************************************
  STATISTICS OF SAVED DATA SET "XDS_ASCII.HKL" (DATA_RANGE=       1    1800)
 FILE TYPE:         XDS_ASCII      MERGE=FALSE          FRIEDEL'S_LAW=TRUE 
 ******************************************************************************

   REFLECTIONS OF TYPE H,0,0  0,K,0  0,0,L OR EXPECTED TO BE ABSENT (*)
   --------------------------------------------------------------------

   H    K    L  RESOLUTION  INTENSITY     SIGMA    INTENSITY/SIGMA  #OBSERVED

    0    0    9    17.949  -0.1456E+00  0.2850E+00        -0.51           4*
    0    0   10    16.155   0.4728E+02  0.1388E+01        34.06           4 
    0    0   11    14.686  -0.5202E-01  0.3385E+00        -0.15           4*
    0    0   12    13.462   0.4227E+02  0.1328E+01        31.84           4 
    0    0   13    12.427  -0.4955E+00  0.3959E+00        -1.25           4*
    0    0   14    11.539   0.6347E+04  0.1501E+03        42.30           4 
    0    0   15    10.770   0.1224E+01  0.5163E+00         2.37           4*
    0    0   16    10.097   0.1161E+04  0.3922E+02        29.60           2 
    0    0   17     9.503   0.6360E+00  0.7831E+00         0.81           2*
    0    0   18     8.975   0.6488E+02  0.2848E+01        22.78           2 
    0    0   19     8.502  -0.6967E+00  0.5049E+00        -1.38           4*
    0    0   20     8.077   0.2274E+03  0.5866E+01        38.76           4 
    0    0   21     7.693   0.2447E+01  0.6913E+00         3.54           4*
    0    0   22     7.343   0.1451E+04  0.3482E+02        41.68           4 
    0    0   23     7.024   0.5352E+00  0.7194E+00         0.74           4*
    0    0   24     6.731   0.3994E+03  0.1004E+02        39.77           4 
    0    0   25     6.462   0.4555E+00  0.7354E+00         0.62           4*
    0    0   26     6.213   0.1208E+01  0.8155E+00         1.48           4 
    0    0   27     5.983   0.9508E+00  0.8208E+00         1.16           4*
    0    0   28     5.769   0.1079E+01  0.1209E+01         0.89           2 
    0    0   29     5.571   0.8639E+00  0.9210E+00         0.94           4*
    0    0   30     5.385   0.1015E+02  0.1691E+01         6.00           2 
    0    0   31     5.211   0.1697E+01  0.1441E+01         1.18           2*
    0    0   32     5.048   0.4210E+03  0.1520E+02        27.70           2 
    0    0   33     4.895   0.7594E+00  0.1040E+01         0.73           4*
    0    0   34     4.751   0.1699E+03  0.4939E+01        34.40           4 
    0    0   35     4.616   0.9529E+00  0.1252E+01         0.76           4*
    0    0   36     4.487   0.3329E+03  0.8817E+01        37.76           4 
    0    0   37     4.366  -0.2420E+00  0.1318E+01        -0.18           4*
    0    0   38     4.251   0.1173E+03  0.5440E+01        21.56           2 
    0    0   39     4.142   0.5690E+01  0.2190E+01         2.60           2*
    0    0   40     4.039   0.8418E+03  0.2947E+02        28.57           2 
    0    0   41     3.940  -0.7202E-01  0.1536E+01        -0.05           4*
    0    0   42     3.846   0.2589E+02  0.2190E+01        11.82           4 
    0    0   43     3.757   0.4085E+01  0.1766E+01         2.31           4*
    0    0   44     3.671   0.1096E+04  0.2697E+02        40.64           4 
    0    0   45     3.590  -0.2095E+01  0.1870E+01        -1.12           4*
    0    0   46     3.512   0.7672E+03  0.1927E+02        39.81           4 
    0    0   47     3.437  -0.2992E+00  0.1979E+01        -0.15           4*
    0    0   48     3.366   0.1804E+03  0.5735E+01        31.46           4 
    0    0   49     3.297   0.1408E+01  0.2096E+01         0.67           4*
    0    0   50     3.231   0.5481E+03  0.1429E+02        38.36           4 
    0    0   51     3.168  -0.1518E+01  0.2004E+01        -0.76           4*
    0    0   52     3.107   0.1055E+01  0.1907E+01         0.55           4 
    0    0   53     3.048   0.2765E+01  0.1903E+01         1.45           4*
    0    0   54     2.992   0.6506E+01  0.1952E+01         3.33           4 
    0    0   55     2.937  -0.1069E+00  0.1787E+01        -0.06           4*
    0    0   56     2.885   0.3773E+02  0.2684E+01        14.05           4 
    0    0   57     2.834  -0.8900E+00  0.1855E+01        -0.48           4*
    0    0   58     2.785   0.1223E+03  0.4617E+01        26.49           4 
    0    0   59     2.738  -0.2308E+01  0.1779E+01        -1.30           4*
    0    0   60     2.692   0.2822E+01  0.1823E+01         1.55           4 
    0    0   61     2.648   0.4092E+00  0.1834E+01         0.22           4*
    0    0   62     2.606   0.2112E+02  0.2279E+01         9.27           4 
    0    0   63     2.564   0.3357E+01  0.2854E+01         1.18           2*
    0    0   64     2.524   0.2001E+02  0.3569E+01         5.61           2 
    0    0   65     2.485   0.3347E+01  0.1866E+01         1.79           4*
    0    0   66     2.448   0.8024E+01  0.2043E+01         3.93           4 
    0    0   67     2.411  -0.1682E+00  0.1865E+01        -0.09           4*
    0    0   68     2.376   0.5331E+01  0.1918E+01         2.78           4 
    0    0   69     2.341  -0.7755E-01  0.1912E+01        -0.04           4*
    0    0   70     2.308   0.5784E+01  0.2810E+01         2.06           2 
    0    0   71     2.275   0.3810E+01  0.2604E+01         1.46           2*
    0    0   72     2.244   0.1316E+02  0.2324E+01         5.66           4 
    0    0   73     2.213   0.3314E+01  0.2138E+01         1.55           4*
    0    0   74     2.183   0.2931E+01  0.2165E+01         1.35           4 
    0    0   75     2.154   0.9454E+00  0.2078E+01         0.46           4*
    0    0   76     2.126   0.3111E+02  0.2869E+01        10.84           4 
    0    0   77     2.098   0.3659E+01  0.2169E+01         1.69           4*
    0    0   78     2.071  -0.1707E+00  0.2067E+01        -0.08           4 
    0    0   79     2.045  -0.2084E+01  0.2136E+01        -0.98           4*
    0    0   80     2.019   0.8783E+01  0.2262E+01         3.88           4 
    0    0   81     1.994   0.3186E+01  0.2112E+01         1.51           4*
    0    0   82     1.970   0.4967E+01  0.2243E+01         2.21           4 
    0    0   83     1.946  -0.5244E+00  0.2066E+01        -0.25           4*
    0    0   84     1.923  -0.3579E+00  0.2091E+01        -0.17           4 
    0    0   85     1.901  -0.1922E+01  0.2042E+01        -0.94           4*
    0    0   86     1.878   0.3014E+01  0.2128E+01         1.42           4 
    0    0   87     1.857   0.4000E+00  0.2087E+01         0.19           4*
    0    0   88     1.836  -0.1379E+01  0.2095E+01        -0.66           4 
    0    0   89     1.815  -0.3380E+00  0.2027E+01        -0.17           4*
    0    0   90     1.795   0.3455E+01  0.2082E+01         1.66           4 
    0    0   91     1.775   0.3632E+01  0.2895E+01         1.25           2*
    0    0   92     1.756   0.1070E+01  0.2026E+01         0.53           4 
    0    0   93     1.737   0.4928E+00  0.2093E+01         0.24           4*
    0    0   94     1.719   0.1275E+01  0.2108E+01         0.60           4 
    0    0   95     1.700  -0.1864E+01  0.2128E+01        -0.88           4*
    0    0   96     1.683  -0.5272E+01  0.3286E+01        -1.60           2 
    0    0   97     1.665  -0.1932E+01  0.3025E+01        -0.64           2*
    0    0   98     1.648   0.3919E+01  0.2196E+01         1.78           4 
    0    0   99     1.632  -0.1103E+01  0.2095E+01        -0.53           4*
    0    0  100     1.615   0.3845E+01  0.2127E+01         1.81           4 
    0    0  101     1.599  -0.1296E+01  0.2087E+01        -0.62           4*
    0    0  102     1.584   0.6391E+00  0.2115E+01         0.30           4 
    0    0  103     1.568   0.6604E+00  0.2250E+01         0.29           4*
    0    0  104     1.553  -0.7320E-01  0.2207E+01        -0.03           4 
    0    0  105     1.539   0.5276E+00  0.2214E+01         0.24           4*
    0    0  106     1.524   0.1541E+01  0.2189E+01         0.70           4 
    0    0  107     1.510  -0.8984E+00  0.2191E+01        -0.41           4*
    0    0  108     1.496   0.1061E+01  0.2260E+01         0.47           4 
    0    0  109     1.482  -0.1001E+01  0.2188E+01        -0.46           4*
    0    0  110     1.469  -0.1549E+01  0.2338E+01        -0.66           4 
    0    0  111     1.455   0.1742E+01  0.2363E+01         0.74           4*
    0    0  112     1.442  -0.7892E+00  0.2255E+01        -0.35           4 
    0    0  113     1.430   0.1214E+01  0.3191E+01         0.38           2*
    0    0  114     1.417  -0.8240E+00  0.3452E+01        -0.24           2 
    0    0  115     1.405  -0.6197E+01  0.3419E+01        -1.81           2*
    0    0  116     1.393   0.1748E+01  0.5193E+01         0.34           1 
    0    8    0    14.957   0.3098E+03  0.7523E+01        41.18           4 
    0   10    0    11.966   0.2684E+03  0.6600E+01        40.66           4 
    0   12    0     9.971   0.6236E+04  0.1474E+03        42.31           4 
    0   14    0     8.547   0.3138E+02  0.1691E+01        18.56           2 
    0   16    0     7.479   0.7923E+01  0.7970E+00         9.94           4 
    0   18    0     6.648   0.1259E+03  0.3522E+01        35.76           4 
    0   20    0     5.983   0.4226E+02  0.1679E+01        25.17           4 
    0   22    0     5.439   0.4133E+03  0.1035E+02        39.93           4 
    0   24    0     4.986   0.7348E+03  0.1800E+02        40.83           4 
    0   26    0     4.602   0.1435E+03  0.4241E+01        33.84           4 
    0   28    0     4.273   0.6360E+03  0.1829E+02        34.77           3 
    0   30    0     3.989   0.1756E+02  0.1864E+01         9.42           4 
    0   32    0     3.739   0.1562E+02  0.1943E+01         8.04           4 
    0   34    0     3.519   0.5002E+02  0.4136E+01        12.10           2 
    0   36    0     3.324   0.1584E+02  0.2232E+01         7.10           4 
    0   38    0     3.149   0.8313E+03  0.2093E+02        39.71           4 
    0   40    0     2.991   0.6128E+01  0.2000E+01         3.06           4 
    0   42    0     2.849   0.2251E+01  0.2909E+01         0.77           2 
    0   44    0     2.719   0.1278E+02  0.2266E+01         5.64           4 
    0   46    0     2.601   0.4635E+02  0.3196E+01        14.50           4 
    0   48    0     2.493   0.6979E+01  0.2260E+01         3.09           4 
    0   50    0     2.393   0.2953E+02  0.3005E+01         9.83           4 
    0   52    0     2.301   0.5907E+02  0.3934E+01        15.02           3 
    0   54    0     2.216   0.4579E+01  0.3070E+01         1.49           2 
    0   56    0     2.137   0.4287E+02  0.3493E+01        12.27           4 
    0   58    0     2.063   0.7325E+01  0.2589E+01         2.83           4 
    0   60    0     1.994   0.9399E+00  0.2540E+01         0.37           3 
    0   62    0     1.930   0.1169E+02  0.2633E+01         4.44           4 
    0   64    0     1.870   0.4867E+01  0.2365E+01         2.06           4 
    0   66    0     1.813   0.1603E+01  0.2218E+01         0.72           4 
    0   68    0     1.760   0.1658E+01  0.2809E+01         0.59           2 
    0   70    0     1.709   0.1521E+01  0.2064E+01         0.74           4 
    0   72    0     1.662   0.6212E+01  0.2132E+01         2.91           4 
    0   74    0     1.617  -0.7721E+00  0.3157E+01        -0.24           2 
    0   76    0     1.574   0.5563E+00  0.1986E+01         0.28           4 
    0   78    0     1.534   0.4569E+01  0.2250E+01         2.03           4 
    0   80    0     1.496   0.2943E+01  0.2232E+01         1.32           4 
    0   82    0     1.459   0.5276E+01  0.2778E+01         1.90           3 
    0   84    0     1.424   0.2102E+01  0.3512E+01         0.60           2 
    6    0    0    16.426   0.8424E+04  0.1989E+03        42.36           4 
    8    0    0    12.320   0.1283E+03  0.3325E+01        38.60           4 
   10    0    0     9.856   0.5106E+03  0.1239E+02        41.22           4 
   12    0    0     8.213   0.3728E+03  0.9215E+01        40.45           4 
   14    0    0     7.040   0.6032E+01  0.9342E+00         6.46           3 
   16    0    0     6.160   0.2800E+03  0.7186E+01        38.97           4 
   18    0    0     5.475   0.5958E+01  0.1040E+01         5.73           4 
   20    0    0     4.928   0.2637E+03  0.7007E+01        37.63           4 
   22    0    0     4.480   0.2054E+02  0.1777E+01        11.56           4 
   24    0    0     4.107   0.1040E+02  0.2066E+01         5.03           3 
   26    0    0     3.791   0.1528E+03  0.4975E+01        30.71           4 
   28    0    0     3.520   0.6884E+03  0.2479E+02        27.77           2 
   30    0    0     3.285   0.1769E+03  0.5831E+01        30.35           4 
   32    0    0     3.080   0.6589E+02  0.3552E+01        18.55           4 
   34    0    0     2.899  -0.3112E+01  0.2281E+01        -1.36           4 
   36    0    0     2.738   0.1080E+03  0.4549E+01        23.74           4 
   38    0    0     2.594   0.1509E+02  0.2834E+01         5.32           3 
   40    0    0     2.464   0.1731E+02  0.2262E+01         7.65           4 
   42    0    0     2.347   0.4325E+02  0.3127E+01        13.83           4 
   44    0    0     2.240   0.7740E+02  0.4035E+01        19.18           4 
   46    0    0     2.143   0.2624E+01  0.2798E+01         0.94           2 
   48    0    0     2.053   0.1763E+02  0.2610E+01         6.76           4 
   50    0    0     1.971   0.9769E+01  0.2297E+01         4.25           4 
   52    0    0     1.895   0.8286E+01  0.2313E+01         3.58           4 
   54    0    0     1.825   0.1195E+01  0.2116E+01         0.56           4 
   56    0    0     1.760   0.1541E+01  0.2100E+01         0.73           4 
   58    0    0     1.699   0.1222E+02  0.3200E+01         3.82           2 
   60    0    0     1.643  -0.1087E+01  0.2141E+01        -0.51           4 
   62    0    0     1.590   0.1115E+01  0.2077E+01         0.54           4 
   64    0    0     1.540   0.3851E+00  0.2130E+01         0.18           4 
   66    0    0     1.493   0.6612E+01  0.3295E+01         2.01           2 
   68    0    0     1.449  -0.6571E+01  0.2740E+01        -2.40           3 

 AVERAGE INTENSITY FOR     198 REFLECTIONS WHICH SHOULD
 BE SYSTEMATICALLY ABSENT IS     1.6% OF MEAN INTENSITY


          COMPLETENESS AND QUALITY OF DATA SET
          ------------------------------------

 R-FACTOR
 observed = (SUM(ABS(I(h,i)-I(h))))/(SUM(I(h,i)))
 expected = expected R-FACTOR derived from Sigma(I)

 COMPARED = number of reflections used for calculating R-FACTOR
 I/SIGMA  = mean of intensity/Sigma(I) of unique reflections
            (after merging symmetry-related observations)
 Sigma(I) = standard deviation of reflection intensity I
            estimated from sample statistics

 R-meas   = redundancy independent R-factor (intensities)
            Diederichs & Karplus (1997), Nature Struct. Biol. 4, 269-275.

 CC(1/2)  = percentage of correlation between intensities from
            random half-datasets. Correlation significant at
            the 0.1% level is marked by an asterisk.
            Karplus & Diederichs (2012), Science 336, 1030-33
 Anomal   = percentage of correlation between random half-sets
  Corr      of anomalous intensity differences. Correlation
            significant at the 0.1% level is marked.
 SigAno   = mean anomalous difference in units of its estimated
            standard deviation (|F(+)-F(-)|/Sigma). F(+), F(-)
            are structure factor estimates obtained from the
            merged intensity observations in each parity class.
  Nano    = Number of unique reflections used to calculate
            Anomal_Corr & SigAno. At least two observations
            for each (+ and -) parity are required.


 SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION
 RESOLUTION     NUMBER OF REFLECTIONS    COMPLETENESS R-FACTOR  R-FACTOR COMPARED I/SIGMA   R-meas  CC(1/2)  Anomal  SigAno   Nano
   LIMIT     OBSERVED  UNIQUE  POSSIBLE     OF DATA   observed  expected                                      Corr

     4.04      102548    8035      8117       99.0%       4.0%      3.9%   102548   59.12      4.2%    99.9*    16*   1.117    6964
     2.89      188095   13689     13689      100.0%       6.7%      5.7%   188095   38.14      7.0%    99.9*     1    0.978   12616
     2.37      241719   17480     17480      100.0%      18.8%     17.8%   241719   14.43     19.6%    99.3*     0    0.858   16396
     2.05      282395   20542     20544      100.0%      47.0%     47.8%   282395    5.97     48.9%    96.3*    -1    0.776   19466
     1.84      330588   23198     23200      100.0%     126.5%    132.7%   330588    2.14    131.2%    76.9*    -1    0.706   22119
     1.68      342292   25592     25594      100.0%     338.1%    361.9%   342292    0.68    351.5%    23.5*     0    0.619   24505
     1.56      383220   27708     27713      100.0%     629.1%    677.2%   383220    0.31    653.2%     5.5     -1    0.562   26632
     1.46      395100   29783     29794      100.0%     894.8%    965.3%   395100    0.18    930.6%     0.6      0    0.541   28691
     1.37      155830   28227     31636       89.2%     944.9%   1020.1%   152966    0.09   1036.7%     2.3      0    0.529   16975
    total     2421787  194254    197767       98.2%      15.2%     15.3%  2418923    7.49     15.9%    99.9*     0    0.686  174364


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES   2436793
 NUMBER OF REJECTED MISFITS                             14484
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                  198
 NUMBER OF ACCEPTED OBSERVATIONS                      2422111
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                 194283



 ******************************************************************************
    WILSON STATISTICS OF DATA SET  "XDS_ASCII.HKL"
 ******************************************************************************

 Data is divided into resolution shells and a straight line 
 A - 2*B*SS is fitted to log<I>, where
   RES    = mean resolution (Angstrom) in shell
   SS     = mean of (sin(THETA)/LAMBDA)**2 in shell
   <I>    = mean reflection intensity in shell
   BO     = (A - log<I>)/(2*SS)
    #     = number of reflections in resolution shell

   WILSON LINE (using all data) : A=   4.951 B=  30.880 CORRELATION=  0.97
      #      RES      SS        <I>       log(<I>)       BO
    2828     7.374   0.005  1.7133E+02       5.144     -20.9
    4612     4.718   0.011  1.6281E+02       5.093      -6.3
    5834     3.715   0.018  1.0251E+02       4.630       8.9
    6825     3.160   0.025  4.3937E+01       3.783      23.3
    7673     2.796   0.032  1.7080E+01       2.838      33.0
    8468     2.535   0.039  9.0068E+00       2.198      35.4
    9164     2.335   0.046  6.1163E+00       1.811      34.2
    9798     2.176   0.053  3.6198E+00       1.286      34.7
   10388     2.046   0.060  2.2554E+00       0.813      34.6
   11007     1.936   0.067  1.2310E+00       0.208      35.6
   11538     1.843   0.074  7.4250E-01      -0.298      35.6
   12057     1.761   0.081  4.4917E-01      -0.800      35.7
   12555     1.690   0.088  3.2407E-01      -1.127      34.7
   13069     1.627   0.094  2.6099E-01      -1.343      33.3
   13509     1.570   0.101  2.0771E-01      -1.572      32.2
   13926     1.519   0.108  1.9368E-01      -1.642      30.4
   14398     1.472   0.115  1.6997E-01      -1.772      29.1
   14678     1.430   0.122  1.6269E-01      -1.816      27.7
   11934     1.394   0.129  1.9588E-01      -1.630      25.6


 HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF  CENTRIC DATA
    AS COMPARED WITH THEORETICAL VALUES. (EXPECTED: 1.00)    
      #      RES        <I**2>/      <I**3>/      <I**4>/  
                         3<I>**2     15<I>**3    105<I>**4 

     505     7.374       1.9307       4.0361       8.9565    
     507     4.718      0.91514      0.82816      0.68397    
     512     3.715       1.3990       2.0425       3.0479    
     510     3.160       1.4344       1.7456       1.9567    
     506     2.796       1.0145       1.1258       1.1990    
     514     2.535      0.90263      0.83437      0.70982    
     508     2.335       1.5555       2.2121       3.1031    
     515     2.176       1.2990       1.8004       2.7533    
     507     2.046       1.0663       1.1242       1.2704    
     515     1.936       1.0613      0.91651      0.78746    
     517     1.843       1.4984       1.4980       1.5960    
     499     1.761       1.7160      0.95926      0.77952    
     515     1.690       2.4755       1.6549       2.0808    
     511     1.627       3.4917       2.1401       3.3509    
     514     1.570       5.4573       3.3906       8.1010    
     505     1.519       6.5486       3.1996       11.058    
     519     1.472       9.1238       6.9922       22.471    
     499     1.430       18.719       13.174       120.67    
     370     1.394       39.137       17.930       430.57    
    9548   overall       4.7936       3.3390       26.956    


 HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF ACENTRIC DATA
    AS COMPARED WITH THEORETICAL VALUES. (EXPECTED: 1.00)    
      #      RES        <I**2>/      <I**3>/      <I**4>/  
                         2<I>**2      6<I>**3     24<I>**4 

    2323     7.374       1.2072       1.8615       3.1952    
    4105     4.718       1.0610       1.1723       1.3560    
    5322     3.715       1.0585       1.1792       1.3421    
    6315     3.160       1.1267       1.3823       1.7233    
    7167     2.796       1.1038       1.3037       1.5673    
    7954     2.535       1.0590       1.1883       1.4073    
    8656     2.335       1.0129       1.1299       1.4077    
    9283     2.176       1.0139       1.0655       1.1868    
    9881     2.046       1.0217       1.0211       1.0326    
   10492     1.936       1.0613       1.0409       1.0329    
   11021     1.843       1.1910       1.1661       1.2046    
   11558     1.761       1.5816       1.5939       1.8913    
   12040     1.690       2.2543       2.1538       2.8076    
   12558     1.627       2.9723       2.8264       4.5459    
   12995     1.570       4.2904       4.1719       9.4927    
   13421     1.519       4.9399       4.6874       12.241    
   13879     1.472       7.7433       7.6501       31.410    
   14179     1.430       15.454       16.695       150.40    
   11564     1.394       36.325       46.613       895.13    
  184713   overall       5.6316       6.3633       72.714    

   ======= CUMULATIVE INTENSITY DISTRIBUTION =======
 DEFINITIONS:
   <I>    = mean reflection intensity
 Na(Z)exp = expected number of acentric reflections with I <= Z*<I>
 Na(Z)obs = observed number of acentric reflections with I <= Z*<I>
 Nc(Z)exp = expected number of  centric reflections with I <= Z*<I>
 Nc(Z)obs = observed number of  centric reflections with I <= Z*<I>



 Nc(Z)obs/Nc(Z)exp versus resolution and Z (0.1-1.0)
      #      RES     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0

     505     7.374  1.01  1.02  1.01  1.03  1.02  1.02  1.02  1.03  1.01  1.02
     507     4.718  1.10  1.08  1.08  1.06  1.03  1.01  1.02  1.01  1.00  0.99
     512     3.715  0.90  0.94  0.93  0.98  0.96  0.96  0.97  0.98  0.95  0.95
     510     3.160  0.94  1.03  1.02  1.02  1.06  1.03  1.02  1.00  0.99  0.97
     506     2.796  0.88  0.91  0.98  0.95  0.97  1.01  1.02  1.02  1.00  1.01
     514     2.535  0.78  0.90  0.96  1.01  1.00  1.01  1.02  1.04  1.03  1.04
     508     2.335  0.62  0.76  0.83  0.90  0.89  0.91  0.92  0.93  0.95  0.95
     515     2.176  0.84  0.76  0.84  0.87  0.92  0.92  0.92  0.95  0.96  0.97
     507     2.046  0.96  0.83  0.84  0.85  0.88  0.90  0.93  0.94  0.95  0.97
     515     1.936  1.06  0.86  0.83  0.80  0.83  0.84  0.85  0.86  0.87  0.88
     517     1.843  1.16  0.96  0.87  0.83  0.82  0.83  0.81  0.80  0.80  0.83
     499     1.761  1.22  0.94  0.82  0.77  0.75  0.72  0.73  0.71  0.74  0.74
     515     1.690  1.68  1.24  1.08  0.97  0.91  0.87  0.84  0.83  0.82  0.81
     511     1.627  1.62  1.19  1.00  0.90  0.84  0.82  0.78  0.76  0.74  0.73
     514     1.570  1.70  1.23  1.04  0.94  0.87  0.83  0.79  0.76  0.73  0.71
     505     1.519  1.79  1.29  1.09  0.97  0.90  0.85  0.81  0.79  0.77  0.76
     519     1.472  1.75  1.27  1.09  0.98  0.89  0.83  0.80  0.78  0.77  0.75
     499     1.430  1.87  1.36  1.14  1.02  0.94  0.87  0.83  0.79  0.77  0.75
     370     1.394  1.86  1.34  1.14  1.01  0.92  0.87  0.83  0.79  0.75  0.73
    9548   overall  1.24  1.04  0.98  0.94  0.92  0.90  0.89  0.88  0.88  0.87


 Na(Z)obs/Na(Z)exp versus resolution and Z (0.1-1.0)
      #      RES     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0

    2323     7.374  1.24  1.19  1.19  1.19  1.18  1.16  1.12  1.11  1.09  1.09
    4105     4.718  1.09  1.07  1.05  1.03  1.02  1.02  1.02  1.02  1.01  1.00
    5322     3.715  1.12  1.17  1.13  1.09  1.07  1.06  1.05  1.04  1.03  1.03
    6315     3.160  1.07  1.14  1.17  1.15  1.12  1.10  1.09  1.08  1.06  1.05
    7167     2.796  0.91  1.03  1.05  1.06  1.07  1.06  1.05  1.05  1.04  1.04
    7954     2.535  0.90  1.00  1.00  1.00  1.02  1.02  1.02  1.02  1.02  1.02
    8656     2.335  0.90  0.93  0.98  0.98  1.00  1.01  1.01  1.02  1.02  1.02
    9283     2.176  1.04  0.94  0.93  0.96  0.97  0.99  1.00  1.01  1.01  1.01
    9881     2.046  1.34  0.99  0.92  0.93  0.94  0.95  0.96  0.98  0.98  0.98
   10492     1.936  1.71  1.15  1.00  0.93  0.90  0.91  0.91  0.92  0.93  0.94
   11021     1.843  2.24  1.38  1.11  0.97  0.91  0.88  0.87  0.87  0.87  0.88
   11558     1.761  2.84  1.64  1.25  1.07  0.97  0.92  0.88  0.86  0.85  0.84
   12040     1.690  3.37  1.89  1.40  1.16  1.03  0.94  0.89  0.85  0.82  0.81
   12558     1.627  3.62  1.98  1.46  1.20  1.05  0.95  0.89  0.85  0.82  0.79
   12995     1.570  3.96  2.17  1.57  1.27  1.10  0.99  0.92  0.86  0.83  0.80
   13421     1.519  3.96  2.15  1.56  1.27  1.10  0.99  0.92  0.86  0.82  0.79
   13879     1.472  4.29  2.32  1.67  1.34  1.15  1.02  0.94  0.88  0.83  0.80
   14179     1.430  4.53  2.42  1.72  1.38  1.17  1.04  0.95  0.88  0.83  0.79
   11564     1.394  4.78  2.54  1.80  1.43  1.21  1.07  0.97  0.89  0.84  0.80
  184713   overall  2.76  1.67  1.32  1.15  1.05  0.99  0.95  0.92  0.90  0.89


 List of    500 reflections *NOT* obeying Wilson distribution (Z> 10.0)

   h    k    l     RES        Z       Intensity    Sigma

   28   70   51    1.38   44.12      0.1728E+02  0.5254E+01 "alien"
   38   70   28    1.39   40.91      0.1603E+02  0.5312E+01 "alien"
   44   46   65    1.40   39.45      0.1545E+02  0.5151E+01 "alien"
   67    9   39    1.38   38.84      0.1521E+02  0.5294E+01 "alien"
   33   59   66    1.38   37.84      0.1482E+02  0.5405E+01 "alien"
   12   18  113    1.38   37.20      0.1457E+02  0.5555E+01 "alien"
   39   57   60    1.38   37.18      0.1457E+02  0.5562E+01 "alien"
   51   47   46    1.41   36.95      0.1447E+02  0.4942E+01 "alien"
   37   43   81    1.38   36.00      0.1410E+02  0.5159E+01 "alien"
   35   17   99    1.38   35.46      0.1389E+02  0.5833E+01 "alien"
   25   21  105    1.39   35.02      0.1372E+02  0.5487E+01 "alien"
   26   68   59    1.38   34.92      0.1368E+02  0.5622E+01 "alien"
   26   80   17    1.38   34.65      0.1357E+02  0.4887E+01 "alien"
   13   25  110    1.38   34.44      0.1349E+02  0.5387E+01 "alien"
   66   20   36    1.38   34.34      0.1345E+02  0.5412E+01 "alien"
   65   33   13    1.39   34.34      0.1345E+02  0.5745E+01 "alien"
   25   13  107    1.39   33.64      0.1318E+02  0.3942E+01 "alien"
   20   62   75    1.38   32.51      0.1274E+02  0.5210E+01 "alien"
   18   34  104    1.38   32.17      0.1260E+02  0.5258E+01 "alien"
   38    6   98    1.39   31.77      0.1245E+02  0.4442E+01 "alien"
   37   57   58    1.42   31.13      0.1013E+02  0.3235E+01 "alien"
   53    5   78    1.38   30.94      0.1212E+02  0.5255E+01 "alien"
   40   58   57    1.38   30.82      0.1207E+02  0.5502E+01 "alien"
   24   60   74    1.39   30.79      0.1206E+02  0.3771E+01 "alien"
   28   52   82    1.38   30.72      0.1204E+02  0.5416E+01 "alien"
    1   45   99    1.39   30.40      0.1191E+02  0.4963E+01 "alien"
   37    5   97    1.41   30.22      0.1184E+02  0.4189E+01 "alien"
   12   22  110    1.40   30.18      0.1182E+02  0.3803E+01 "alien"
   50   32   70    1.39   30.10      0.1179E+02  0.4160E+01 "alien"
   31   67   54    1.38   29.55      0.1157E+02  0.4958E+01 "alien"
   69   19   10    1.39   29.30      0.1148E+02  0.5246E+01 "alien"
   31   47   85    1.37   29.23      0.1145E+02  0.5578E+01 "alien"
   52   52   31    1.41   29.23      0.1145E+02  0.5049E+01 "alien"
   42   12   93    1.38   29.05      0.1138E+02  0.6381E+01 "alien"
   22   34  102    1.37   29.02      0.1137E+02  0.5298E+01 "alien"
   40   28   88    1.39   28.99      0.1136E+02  0.4033E+01 "alien"
   40    2   94    1.41   28.78      0.1128E+02  0.4055E+01 "alien"
   17   77   44    1.39   28.76      0.1127E+02  0.5007E+01 "alien"
   22   30  103    1.39   28.45      0.1115E+02  0.5547E+01 "alien"
   48   44   61    1.39   28.43      0.1114E+02  0.5051E+01 "alien"
   64   10   51    1.38   28.43      0.1114E+02  0.5788E+01 "alien"
   70    8   20    1.38   28.39      0.1112E+02  0.5263E+01 "alien"
   54   50   26    1.41   28.30      0.9209E+01  0.4853E+01 "alien"
   43   19   89    1.39   28.26      0.1107E+02  0.4145E+01 "alien"
   48    4   86    1.38   28.25      0.1107E+02  0.7251E+01 "alien"
   34   48   80    1.38   28.23      0.1106E+02  0.5484E+01 "alien"
   28   14  106    1.38   28.15      0.1103E+02  0.5838E+01 "alien"
   44   38   75    1.39   28.11      0.1101E+02  0.5043E+01 "alien"
   68   10   30    1.39   27.91      0.1093E+02  0.3062E+01 "alien"
   42   34   82    1.39   27.69      0.1085E+02  0.4976E+01 "alien"
   39   55   63    1.39   27.53      0.1078E+02  0.5449E+01 "alien"
   33   31   95    1.38   27.40      0.1074E+02  0.4898E+01 "alien"
   57   47   18    1.41   27.32      0.8890E+01  0.4569E+01 "alien"
   44   52   58    1.39   27.21      0.1066E+02  0.5372E+01 "alien"
   15   17  112    1.38   27.20      0.1066E+02  0.3523E+01 "alien"
   42   50   61    1.42   27.18      0.8843E+01  0.2981E+01 "alien"
   69    9   28    1.38   27.05      0.1060E+02  0.5033E+01 "alien"
   57   25   60    1.39   27.03      0.1059E+02  0.4101E+01 "alien"
   60   26   50    1.40   27.02      0.1059E+02  0.6059E+01 "alien"
   41   67   29    1.39   26.87      0.1052E+02  0.5017E+01 "alien"
   71    7    9    1.38   26.82      0.1051E+02  0.5761E+01 "alien"
   36   58   64    1.38   26.82      0.1051E+02  0.5458E+01 "alien"
   53   47   42    1.40   26.77      0.1049E+02  0.4961E+01 "alien"
   37   61   55    1.39   26.75      0.1048E+02  0.5156E+01 "alien"
   42   64   38    1.38   26.52      0.1039E+02  0.5130E+01 "alien"
   48   24   80    1.38   26.50      0.1038E+02  0.4024E+01 "alien"
   11   33  105    1.40   26.45      0.1036E+02  0.4554E+01 "alien"
   60   32   45    1.39   26.40      0.1034E+02  0.5835E+01 "alien"
   56   36   47    1.42   26.39      0.8586E+01  0.3139E+01 "alien"
   37   67   39    1.40   26.28      0.1030E+02  0.5196E+01 "alien"
   27   61   69    1.39   26.18      0.1026E+02  0.3898E+01 "alien"
   40   66   39    1.38   26.18      0.1026E+02  0.5459E+01 "alien"
   26   64   67    1.38   26.01      0.1019E+02  0.6093E+01 "alien"
   33   61   62    1.39   25.90      0.1015E+02  0.5477E+01 "alien"
   32   44   87    1.37   25.69      0.1006E+02  0.5878E+01 "alien"
   44   32   80    1.39   25.51      0.9992E+01  0.4108E+01 "alien"
   40   54   63    1.39   25.47      0.9977E+01  0.5542E+01 "alien"
   42   14   92    1.39   25.39      0.9945E+01  0.5348E+01 "alien"
   38   56   59    1.41   25.17      0.8191E+01  0.3190E+01 "alien"
   33   61   63    1.38   25.11      0.9835E+01  0.5373E+01 "alien"
   38   18   96    1.38   25.08      0.9824E+01  0.5789E+01 "alien"
   19   29  106    1.38   25.03      0.9806E+01  0.5076E+01 "alien"
   28   46   86    1.40   25.01      0.9799E+01  0.4936E+01 "alien"
    9   23  109    1.41   24.99      0.8132E+01  0.2854E+01 "alien"
   62   40    4    1.40   24.99      0.9790E+01  0.4631E+01 "alien"
   37   35   87    1.39   24.98      0.9786E+01  0.4706E+01 "alien"
   37    9   97    1.40   24.94      0.9768E+01  0.5893E+01 "alien"
   32   70   44    1.38   24.77      0.9702E+01  0.4838E+01 "alien"
   29   23  102    1.38   24.75      0.9696E+01  0.5518E+01 "alien"
   71    7    8    1.38   24.75      0.9695E+01  0.5279E+01 "alien"
   32   14  101    1.40   24.73      0.9687E+01  0.5982E+01 "alien"
    9   81   38    1.38   24.72      0.9682E+01  0.4930E+01 "alien"
   63   25   44    1.38   24.68      0.9668E+01  0.6416E+01 "alien"
   14    4  115    1.38   24.47      0.9585E+01  0.5564E+01 "alien"
   10   44   99    1.39   24.42      0.9568E+01  0.5554E+01 "alien"
   41   55   59    1.39   24.39      0.9553E+01  0.4069E+01 "alien"
   26   18  104    1.40   24.34      0.9535E+01  0.3819E+01 "alien"
   40   10   95    1.39   24.33      0.9533E+01  0.4264E+01 "alien"
   26   52   84    1.38   24.32      0.9529E+01  0.5325E+01 "alien"
   47   37   68    1.41   24.31      0.7911E+01  0.3986E+01 "alien"
   36   30   92    1.39   24.27      0.9506E+01  0.5201E+01 "alien"
   17   25  107    1.40   24.18      0.9474E+01  0.3147E+01 "alien"
   50   28   70    1.41   24.18      0.7866E+01  0.2694E+01 "alien"
   15   81   34    1.38   24.10      0.9440E+01  0.4676E+01 "alien"
   35   21   98    1.38   24.09      0.9436E+01  0.5981E+01 "alien"
   39    9   94    1.41   24.07      0.7832E+01  0.2366E+01 "alien"
    5   49   96    1.38   23.92      0.9371E+01  0.5714E+01 "alien"
    3   57   88    1.38   23.85      0.9342E+01  0.5053E+01 "alien"
   30   64   58    1.40   23.84      0.9339E+01  0.3901E+01 "alien"
   50   56   28    1.41   23.78      0.9315E+01  0.5467E+01 "alien"
   59   27   55    1.38   23.77      0.9314E+01  0.6187E+01 "alien"
   27   55   75    1.41   23.69      0.7708E+01  0.3160E+01 "alien"
   30   70   47    1.39   23.68      0.9276E+01  0.4979E+01 "alien"
   37   15   98    1.38   23.66      0.9270E+01  0.5932E+01 "alien"
   15   83   23    1.38   23.57      0.9235E+01  0.5218E+01 "alien"
   17   77   46    1.38   23.50      0.9205E+01  0.4912E+01 "alien"
   58   30   54    1.39   23.48      0.9199E+01  0.5653E+01 "alien"
   42   60   48    1.38   23.46      0.9189E+01  0.5267E+01 "alien"
   56   30   58    1.39   23.44      0.9182E+01  0.3912E+01 "alien"
   27   77   17    1.41   23.36      0.7602E+01  0.2219E+01 "alien"
   43   67   18    1.39   23.33      0.9141E+01  0.4905E+01 "alien"
   24   72   49    1.40   23.31      0.9131E+01  0.2860E+01 "alien"
   24   28  103    1.39   23.26      0.9114E+01  0.4913E+01 "alien"
   31   33   95    1.39   23.23      0.9102E+01  0.4891E+01 "alien"
   10   20  113    1.38   23.22      0.9098E+01  0.5014E+01 "alien"
   40   66   36    1.39   23.21      0.9094E+01  0.5164E+01 "alien"
   55   27   64    1.39   23.15      0.9070E+01  0.4103E+01 "alien"
   26   60   70    1.40   23.15      0.9068E+01  0.3671E+01 "alien"
   29   11  106    1.38   23.09      0.9046E+01  0.5606E+01 "alien"
   40   14   95    1.38   23.05      0.9029E+01  0.6073E+01 "alien"
   50   56    4    1.45   23.05      0.7498E+01  0.2522E+01 "alien"
   24   14  108    1.39   23.01      0.9014E+01  0.3981E+01 "alien"
   28   56   74    1.40   23.01      0.9014E+01  0.3757E+01 "alien"
    7   47   97    1.39   23.00      0.9012E+01  0.5119E+01 "alien"
   24   72   50    1.39   22.96      0.8996E+01  0.3042E+01 "alien"
   48   50   50    1.40   22.95      0.8991E+01  0.5126E+01 "alien"
   10   82   22    1.42   22.92      0.7457E+01  0.2281E+01 "alien"
   12   32  106    1.39   22.88      0.8962E+01  0.4563E+01 "alien"
   50   32   72    1.38   22.81      0.8938E+01  0.6278E+01 "alien"
   31   35   94    1.38   22.77      0.8920E+01  0.4900E+01 "alien"
   47   53   47    1.40   22.75      0.8914E+01  0.5127E+01 "alien"
   17   81   29    1.39   22.74      0.8908E+01  0.4752E+01 "alien"
   22   28  105    1.38   22.74      0.8907E+01  0.5281E+01 "alien"
   43   23   87    1.39   22.70      0.8892E+01  0.4221E+01 "alien"
   56   30   60    1.38   22.61      0.8857E+01  0.5775E+01 "alien"
   57   21   63    1.39   22.60      0.8852E+01  0.5092E+01 "alien"
   46   58   39    1.40   22.59      0.8851E+01  0.3654E+01 "alien"
   68   24    9    1.39   22.57      0.8840E+01  0.3666E+01 "alien"
   28   78   24    1.38   22.54      0.8830E+01  0.4818E+01 "alien"
   11   41  101    1.39   22.53      0.8828E+01  0.4821E+01 "alien"
   52   40   58    1.39   22.53      0.8824E+01  0.5193E+01 "alien"
   69   15   18    1.39   22.42      0.8782E+01  0.3811E+01 "alien"
   34   76    6    1.38   22.38      0.8768E+01  0.5071E+01 "alien"
   45    5   90    1.39   22.38      0.8767E+01  0.6891E+01 "alien"
   23   37   98    1.39   22.29      0.8733E+01  0.3690E+01 "alien"
   44   36   78    1.38   22.28      0.8729E+01  0.5206E+01 "alien"
   32   50   78    1.40   22.28      0.8728E+01  0.3793E+01 "alien"
   61   31   42    1.39   22.27      0.8722E+01  0.3784E+01 "alien"
   64   26   38    1.38   22.26      0.8719E+01  0.5665E+01 "alien"
   68   26    7    1.38   22.25      0.8716E+01  0.3669E+01 "alien"
   16   26  108    1.39   22.23      0.8710E+01  0.3848E+01 "alien"
   68   22   19    1.38   22.22      0.8705E+01  0.3778E+01 "alien"
   33   53   76    1.37   22.21      0.8700E+01  0.5723E+01 "alien"
   36   12   98    1.40   22.14      0.8672E+01  0.4061E+01 "alien"
   14   84    3    1.40   22.13      0.8671E+01  0.4851E+01 "alien"
   34   16  100    1.39   22.06      0.8640E+01  0.6175E+01 "alien"
   55   43   44    1.39   22.04      0.8633E+01  0.5177E+01 "alien"
   21   57   80    1.39   22.00      0.8617E+01  0.3672E+01 "alien"
   62    8   55    1.39   21.99      0.8615E+01  0.3041E+01 "alien"
   30   78    4    1.39   21.96      0.8602E+01  0.3361E+01 "alien"
   39   69   27    1.39   21.94      0.8595E+01  0.4888E+01 "alien"
   32   18  101    1.39   21.86      0.8562E+01  0.4220E+01 "alien"
   13   23  111    1.38   21.84      0.8555E+01  0.5022E+01 "alien"
   59   23   58    1.38   21.82      0.8547E+01  0.6441E+01 "alien"
   51   33   69    1.38   21.81      0.8545E+01  0.6515E+01 "alien"
   45   61   34    1.40   21.80      0.8540E+01  0.3433E+01 "alien"
   39    9   96    1.39   21.76      0.8523E+01  0.6255E+01 "alien"
   20   14  108    1.41   21.70      0.7060E+01  0.2303E+01 "alien"
   34   14  101    1.38   21.67      0.8488E+01  0.5611E+01 "alien"
   38   68   36    1.39   21.66      0.8484E+01  0.5081E+01 "alien"
   30   70   48    1.38   21.65      0.8480E+01  0.4879E+01 "alien"
   57   41   38    1.40   21.57      0.8452E+01  0.2978E+01 "alien"
   67   27   15    1.38   21.56      0.8446E+01  0.3835E+01 "alien"
   57   33   52    1.39   21.51      0.8426E+01  0.3870E+01 "alien"
   53   53    9    1.43   21.48      0.6989E+01  0.2939E+01 "alien"
   38   24   93    1.39   21.47      0.8411E+01  0.4046E+01 "alien"
   16   40  100    1.39   21.47      0.8409E+01  0.5376E+01 "alien"
   56   38   50    1.39   21.47      0.8409E+01  0.5932E+01 "alien"
   64   34   17    1.40   21.44      0.8398E+01  0.3777E+01 "alien"
   55   47   28    1.42   21.43      0.6973E+01  0.2915E+01 "alien"
   26   60   73    1.38   21.39      0.8380E+01  0.5329E+01 "alien"
   61   37   22    1.42   21.35      0.6947E+01  0.2232E+01 "alien"
   32   54   74    1.39   21.34      0.8360E+01  0.3828E+01 "alien"
   51   41   57    1.40   21.30      0.8346E+01  0.3668E+01 "alien"
   40   50   65    1.41   21.27      0.6922E+01  0.3070E+01 "alien"
   20   68   60    1.41   21.27      0.6921E+01  0.2890E+01 "alien"
   17   71   62    1.37   21.26      0.8330E+01  0.4723E+01 "alien"
    9    1  115    1.39   21.25      0.8325E+01  0.3719E+01 "alien"
   51   19   78    1.38   21.22      0.8313E+01  0.3901E+01 "alien"
   47   37   72    1.38   21.19      0.8303E+01  0.5042E+01 "alien"
   57   23   61    1.39   21.04      0.8243E+01  0.4088E+01 "alien"
   23   29  103    1.39   21.03      0.8240E+01  0.5349E+01 "alien"
   46   56   44    1.40   20.99      0.8223E+01  0.5521E+01 "alien"
   37   57   65    1.37   20.98      0.8219E+01  0.5439E+01 "alien"
    7   31  109    1.38   20.96      0.8213E+01  0.5284E+01 "alien"
   39   67   38    1.38   20.96      0.8210E+01  0.5097E+01 "alien"
   14   46   97    1.38   20.90      0.8189E+01  0.5495E+01 "alien"
   45    3   90    1.39   20.84      0.8166E+01  0.4647E+01 "alien"
    4   84   25    1.39   20.84      0.8164E+01  0.4963E+01 "alien"
   44   34   80    1.38   20.80      0.8147E+01  0.5086E+01 "alien"
   18   28  107    1.38   20.79      0.8146E+01  0.5333E+01 "alien"
   53   39   52    1.42   20.74      0.6749E+01  0.2913E+01 "alien"
    5   31  109    1.38   20.73      0.8123E+01  0.4659E+01 "alien"
   36   70   35    1.38   20.72      0.8118E+01  0.4737E+01 "alien"
   71    7    4    1.38   20.69      0.8104E+01  0.3560E+01 "alien"
   39   55   62    1.39   20.63      0.8081E+01  0.3713E+01 "alien"
   16   82    2    1.42   20.63      0.6711E+01  0.2691E+01 "alien"
   40   10   96    1.38   20.60      0.8071E+01  0.6201E+01 "alien"
   21    1  112    1.38   20.60      0.8071E+01  0.5693E+01 "alien"
   55   43   41    1.41   20.60      0.8070E+01  0.2938E+01 "alien"
   63    9   53    1.38   20.51      0.8034E+01  0.3202E+01 "alien"
   70   14   13    1.38   20.49      0.8028E+01  0.5216E+01 "alien"
   65   31   24    1.38   20.42      0.7998E+01  0.5355E+01 "alien"
   22   64   70    1.38   20.41      0.7995E+01  0.5513E+01 "alien"
   53    3   78    1.38   20.39      0.7988E+01  0.5361E+01 "alien"
   61   37   32    1.39   20.33      0.7964E+01  0.5342E+01 "alien"
   12   30  105    1.41   20.33      0.6614E+01  0.2865E+01 "alien"
   59   25   55    1.39   20.29      0.7950E+01  0.3863E+01 "alien"
   64   34   20    1.39   20.28      0.7945E+01  0.5456E+01 "alien"
   38   60   51    1.41   20.23      0.6583E+01  0.2987E+01 "alien"
   20   52   88    1.38   20.21      0.7915E+01  0.3977E+01 "alien"
    8   50   92    1.41   20.16      0.7899E+01  0.2484E+01 "alien"
   25   79   10    1.41   20.08      0.7865E+01  0.4822E+01 "alien"
   46   50   53    1.41   20.07      0.6531E+01  0.2981E+01 "alien"
   55   23   65    1.40   20.05      0.7856E+01  0.3970E+01 "alien"
   15    9  114    1.38   20.05      0.7853E+01  0.5488E+01 "alien"
   33   77    4    1.38   20.04      0.7852E+01  0.3535E+01 "alien"
   49   43   59    1.40   20.03      0.7846E+01  0.4754E+01 "alien"
   35   63   57    1.38   20.02      0.7845E+01  0.5054E+01 "alien"
   12   18  110    1.41   20.01      0.6510E+01  0.2230E+01 "alien"
   41   63   43    1.39   20.01      0.7838E+01  0.5197E+01 "alien"
   27   47   86    1.40   19.98      0.7826E+01  0.5024E+01 "alien"
   49   41   60    1.41   19.94      0.6486E+01  0.2919E+01 "alien"
   17   57   84    1.38   19.92      0.7803E+01  0.5564E+01 "alien"
   23   59   75    1.40   19.91      0.7801E+01  0.3615E+01 "alien"
   14    2  115    1.38   19.90      0.7798E+01  0.3934E+01 "alien"
   63   27   40    1.39   19.83      0.7768E+01  0.5423E+01 "alien"
   12   84    6    1.40   19.79      0.7753E+01  0.3327E+01 "alien"
   23   13  107    1.41   19.78      0.7749E+01  0.3101E+01 "alien"
   68    2   32    1.39   19.69      0.7712E+01  0.2576E+01 "alien"
   36   64   51    1.39   19.67      0.7705E+01  0.4852E+01 "alien"
    4   70   67    1.39   19.61      0.7681E+01  0.2891E+01 "alien"
   65   17   44    1.37   19.58      0.7671E+01  0.6066E+01 "alien"
   23   53   85    1.38   19.56      0.7662E+01  0.4885E+01 "alien"
   38   52   68    1.39   19.50      0.7638E+01  0.4201E+01 "alien"
   67    9   28    1.42   19.50      0.6344E+01  0.2501E+01 "alien"
   57   25   62    1.38   19.48      0.7632E+01  0.5646E+01 "alien"
   33   41   85    1.41   19.45      0.7620E+01  0.3204E+01 "alien"
   43   67   13    1.40   19.44      0.7616E+01  0.3363E+01 "alien"
   22   80   26    1.38   19.42      0.7610E+01  0.3470E+01 "alien"
   14   32  106    1.38   19.42      0.7609E+01  0.4808E+01 "alien"
   14   50   89    1.42   19.41      0.6315E+01  0.2094E+01 "alien"
   22   44   91    1.41   19.40      0.6314E+01  0.2289E+01 "alien"
   40   58   52    1.41   19.40      0.7598E+01  0.3060E+01 "alien"
   60   40   23    1.41   19.38      0.6307E+01  0.2866E+01 "alien"
   21   79   32    1.39   19.37      0.7589E+01  0.3331E+01 "alien"
   58   22   60    1.39   19.35      0.7579E+01  0.3689E+01 "alien"
   32   68   50    1.38   19.35      0.7579E+01  0.4834E+01 "alien"
   52   18   76    1.38   19.30      0.7562E+01  0.4014E+01 "alien"
   11   27  110    1.38   19.28      0.7552E+01  0.4778E+01 "alien"
    4   34  105    1.41   19.25      0.7543E+01  0.3240E+01 "alien"
   46   60    1    1.46   19.25      0.6545E+01  0.2442E+01 "alien"
    3   67   74    1.38   19.24      0.7538E+01  0.3363E+01 "alien"
   30   60   64    1.41   19.21      0.6252E+01  0.3664E+01 "alien"
   50   32   69    1.40   19.19      0.7520E+01  0.3060E+01 "alien"
   26   58   74    1.39   19.17      0.7512E+01  0.5055E+01 "alien"
   18   34  103    1.39   19.17      0.7511E+01  0.5312E+01 "alien"
   47   17   82    1.41   19.17      0.7509E+01  0.2875E+01 "alien"
   43   65   30    1.39   19.15      0.7500E+01  0.4554E+01 "alien"
   18   76   44    1.40   19.12      0.7490E+01  0.3358E+01 "alien"
   39   69    9    1.43   19.11      0.6217E+01  0.2461E+01 "alien"
    4   22  111    1.40   19.10      0.7484E+01  0.3307E+01 "alien"
   34   68   44    1.39   19.10      0.7483E+01  0.4840E+01 "alien"
   18   82   23    1.38   19.07      0.7469E+01  0.4706E+01 "alien"
   14   10  113    1.39   19.02      0.7450E+01  0.3669E+01 "alien"
   22   68   54    1.44   19.01      0.6186E+01  0.1616E+01 "alien"
   19   51   87    1.40   18.98      0.7437E+01  0.2896E+01 "alien"
   16   82   23    1.39   18.97      0.7433E+01  0.4608E+01 "alien"
    5   33  106    1.40   18.96      0.7426E+01  0.3168E+01 "alien"
   15   21  111    1.38   18.94      0.7420E+01  0.5060E+01 "alien"
   58   44    5    1.44   18.90      0.6150E+01  0.2244E+01 "alien"
   16   58   81    1.40   18.88      0.7395E+01  0.3451E+01 "alien"
   59   35   44    1.39   18.85      0.7385E+01  0.5703E+01 "alien"
   56   48   14    1.43   18.84      0.6130E+01  0.2143E+01 "alien"
   29   65   61    1.38   18.81      0.7370E+01  0.4921E+01 "alien"
   31   57   69    1.40   18.81      0.7367E+01  0.3953E+01 "alien"
    3   19  113    1.39   18.77      0.7355E+01  0.4919E+01 "alien"
   40   62   50    1.37   18.77      0.7354E+01  0.5064E+01 "alien"
    6   52   93    1.38   18.75      0.7345E+01  0.4626E+01 "alien"
   59   41   19    1.43   18.74      0.6097E+01  0.2063E+01 "alien"
   70    4   22    1.38   18.73      0.7337E+01  0.4985E+01 "alien"
   46   22   83    1.39   18.73      0.7336E+01  0.4069E+01 "alien"
    2   42  100    1.40   18.71      0.7330E+01  0.4603E+01 "alien"
   34   40   86    1.39   18.71      0.7329E+01  0.3901E+01 "alien"
   33   57   68    1.39   18.69      0.7323E+01  0.5572E+01 "alien"
    4   74   61    1.38   18.69      0.7323E+01  0.5063E+01 "alien"
   41   71    6    1.38   18.66      0.7311E+01  0.3439E+01 "alien"
   35    9   99    1.40   18.66      0.7310E+01  0.3979E+01 "alien"
    6   58   86    1.38   18.65      0.7307E+01  0.4975E+01 "alien"
   47   27   80    1.38   18.65      0.7304E+01  0.3952E+01 "alien"
    7   67   74    1.38   18.63      0.7297E+01  0.4966E+01 "alien"
   69    1   26    1.39   18.62      0.7296E+01  0.2537E+01 "alien"
   11    1  114    1.40   18.62      0.7296E+01  0.3600E+01 "alien"
   15   75   51    1.39   18.60      0.7288E+01  0.2773E+01 "alien"
   24   54   80    1.40   18.60      0.7288E+01  0.3584E+01 "alien"
   38   60   56    1.39   18.53      0.7259E+01  0.5392E+01 "alien"
   18   60   78    1.39   18.51      0.7252E+01  0.3784E+01 "alien"
   33   63   60    1.38   18.48      0.7238E+01  0.5162E+01 "alien"
   35   73    4    1.42   18.47      0.6010E+01  0.2495E+01 "alien"
    4   20  114    1.38   18.47      0.7236E+01  0.4778E+01 "alien"
   27    7  105    1.41   18.44      0.6001E+01  0.3159E+01 "alien"
   54   26   67    1.39   18.42      0.7217E+01  0.4185E+01 "alien"
   65   31   25    1.38   18.42      0.7215E+01  0.5606E+01 "alien"
   40    6   95    1.40   18.41      0.7212E+01  0.4197E+01 "alien"
   28   76   28    1.39   18.41      0.7212E+01  0.3308E+01 "alien"
   19   81   28    1.38   18.39      0.7204E+01  0.4674E+01 "alien"
   27   71   46    1.40   18.36      0.7193E+01  0.2503E+01 "alien"
   38   42   81    1.38   18.35      0.7187E+01  0.5099E+01 "alien"
   61   11   59    1.38   18.34      0.7184E+01  0.3713E+01 "alien"
   45   57   42    1.41   18.33      0.7181E+01  0.3527E+01 "alien"
   28   64   63    1.39   18.33      0.7180E+01  0.3826E+01 "alien"
   26   34   98    1.39   18.32      0.7179E+01  0.3424E+01 "alien"
   70   10   17    1.38   18.32      0.7178E+01  0.3488E+01 "alien"
   19   69   64    1.38   18.32      0.7177E+01  0.4825E+01 "alien"
   31   71   43    1.38   18.32      0.7177E+01  0.4999E+01 "alien"
   46   16   87    1.38   18.28      0.7163E+01  0.4368E+01 "alien"
   24   66   59    1.42   18.27      0.5944E+01  0.2181E+01 "alien"
   34   76    9    1.38   18.27      0.7156E+01  0.3413E+01 "alien"
    4   76   53    1.40   18.26      0.7155E+01  0.2832E+01 "alien"
   35   53   73    1.38   18.25      0.7151E+01  0.5395E+01 "alien"
   68   20   24    1.38   18.25      0.7149E+01  0.3831E+01 "alien"
   58   24   53    1.42   18.21      0.5925E+01  0.1953E+01 "alien"
   71    7    1    1.38   18.21      0.7132E+01  0.3545E+01 "alien"
   30   58   72    1.38   18.20      0.7130E+01  0.5424E+01 "alien"
   15   73   58    1.38   18.19      0.7125E+01  0.4660E+01 "alien"
   33   67   51    1.38   18.14      0.7108E+01  0.4861E+01 "alien"
   14    2  113    1.40   18.14      0.7107E+01  0.3731E+01 "alien"
   19   35  103    1.37   18.14      0.7107E+01  0.5583E+01 "alien"
   33   17  101    1.38   18.12      0.7097E+01  0.5643E+01 "alien"
    9   47   97    1.38   18.11      0.7096E+01  0.4692E+01 "alien"
   53   47   41    1.40   18.08      0.7083E+01  0.4829E+01 "alien"
   71    3   11    1.38   18.07      0.7081E+01  0.5111E+01 "alien"
   32   56   73    1.38   18.02      0.7059E+01  0.5294E+01 "alien"
   51   47   49    1.39   18.01      0.7056E+01  0.4890E+01 "alien"
   30   34   96    1.38   17.99      0.7049E+01  0.4969E+01 "alien"
   65   31   21    1.39   17.99      0.7049E+01  0.5677E+01 "alien"
   36   66   47    1.38   17.99      0.7048E+01  0.4675E+01 "alien"
   20   26  106    1.39   17.99      0.7047E+01  0.4703E+01 "alien"
   51   55   23    1.42   17.97      0.5847E+01  0.5287E+01 "alien"
   45   53   54    1.39   17.94      0.7027E+01  0.5624E+01 "alien"
   41   45   72    1.40   17.91      0.7018E+01  0.5006E+01 "alien"
    6   50   94    1.39   17.91      0.7014E+01  0.2797E+01 "alien"
   27   13  105    1.40   17.88      0.7004E+01  0.3062E+01 "alien"
   35   19   99    1.38   17.87      0.7001E+01  0.5386E+01 "alien"
   46   44   62    1.41   17.85      0.5809E+01  0.2234E+01 "alien"
   26   42   91    1.40   17.84      0.6990E+01  0.2541E+01 "alien"
    8   22  112    1.39   17.83      0.6983E+01  0.3469E+01 "alien"
   62   14   49    1.41   17.80      0.5793E+01  0.2405E+01 "alien"
   20   38   97    1.41   17.80      0.5792E+01  0.2224E+01 "alien"
   65   29   26    1.39   17.80      0.6972E+01  0.5437E+01 "alien"
   59   43   23    1.40   17.77      0.6963E+01  0.5049E+01 "alien"
   12   44   99    1.38   17.75      0.6955E+01  0.5399E+01 "alien"
   18   82   24    1.38   17.75      0.6954E+01  0.4912E+01 "alien"
   42   60   44    1.40   17.73      0.6945E+01  0.3040E+01 "alien"
   40   60   54    1.38   17.73      0.6944E+01  0.5217E+01 "alien"
   39   19   94    1.39   17.71      0.6939E+01  0.4052E+01 "alien"
   44   42   71    1.39   17.71      0.6937E+01  0.4849E+01 "alien"
   34   34   90    1.40   17.70      0.6935E+01  0.2638E+01 "alien"
   60    8   60    1.40   17.69      0.6930E+01  0.2790E+01 "alien"
   17   83   13    1.39   17.69      0.6929E+01  0.3299E+01 "alien"
   39   45   73    1.41   17.62      0.5732E+01  0.2928E+01 "alien"
   34   54   69    1.41   17.60      0.6894E+01  0.3852E+01 "alien"
   69    9    9    1.42   17.59      0.5725E+01  0.2183E+01 "alien"
   56   36   53    1.39   17.57      0.6884E+01  0.5635E+01 "alien"
   50   20   78    1.39   17.55      0.6877E+01  0.4273E+01 "alien"
    5   25  112    1.38   17.55      0.6877E+01  0.4942E+01 "alien"
   32   56   72    1.38   17.52      0.6862E+01  0.5388E+01 "alien"
   48   46   59    1.39   17.49      0.6851E+01  0.5173E+01 "alien"
   44   56   41    1.44   17.48      0.5687E+01  0.2168E+01 "alien"
   51   11   80    1.38   17.48      0.6848E+01  0.4078E+01 "alien"
    8   14  115    1.38   17.47      0.6844E+01  0.3733E+01 "alien"
   46    4   89    1.38   17.47      0.6843E+01  0.6690E+01 "alien"
   13    9  114    1.39   17.47      0.6843E+01  0.5323E+01 "alien"
    5   33  105    1.41   17.46      0.5681E+01  0.2878E+01 "alien"
   47   53   48    1.40   17.45      0.6836E+01  0.4928E+01 "alien"
   10   84   15    1.40   17.45      0.6834E+01  0.3524E+01 "alien"
   66   24   26    1.39   17.44      0.6833E+01  0.3161E+01 "alien"
   29   59   67    1.41   17.43      0.5671E+01  0.3829E+01 "alien"
   24   78   27    1.40   17.42      0.6824E+01  0.3349E+01 "alien"
   40   36   82    1.40   17.42      0.6823E+01  0.4832E+01 "alien"
   31   13  102    1.40   17.42      0.6822E+01  0.5523E+01 "alien"
   20   82   19    1.38   17.41      0.6821E+01  0.4576E+01 "alien"
   37   65   48    1.38   17.41      0.6820E+01  0.5059E+01 "alien"
   50   16   79    1.39   17.40      0.6815E+01  0.3560E+01 "alien"
   60   26   53    1.38   17.38      0.6808E+01  0.5906E+01 "alien"
   20   82   13    1.39   17.38      0.6808E+01  0.3249E+01 "alien"
   50   50   43    1.41   17.38      0.5654E+01  0.4796E+01 "alien"
   70    4   23    1.38   17.37      0.6806E+01  0.5404E+01 "alien"
   14   84   10    1.39   17.37      0.6804E+01  0.3107E+01 "alien"
   52   10   79    1.38   17.36      0.6801E+01  0.4970E+01 "alien"
   57   31   51    1.41   17.35      0.5644E+01  0.2945E+01 "alien"
   45   37   70    1.43   17.34      0.5643E+01  0.1691E+01 "alien"
   29   75   22    1.42   17.34      0.5641E+01  0.2128E+01 "alien"
   62   30   39    1.39   17.34      0.6791E+01  0.3829E+01 "alien"
   37   55   62    1.41   17.32      0.5634E+01  0.2938E+01 "alien"
   36   56   68    1.37   17.31      0.6781E+01  0.5444E+01 "alien"
   63    5   52    1.39   17.31      0.6780E+01  0.2662E+01 "alien"
   48   28   76    1.40   17.31      0.6780E+01  0.3888E+01 "alien"
   45   53   53    1.40   17.30      0.6779E+01  0.5229E+01 "alien"
   17   41   95    1.42   17.29      0.5627E+01  0.1760E+01 "alien"
    4   70   64    1.41   17.27      0.5618E+01  0.2435E+01 "alien"
   67   27    2    1.40   17.26      0.6762E+01  0.4017E+01 "alien"
   66   20   32    1.39   17.26      0.6762E+01  0.3038E+01 "alien"
   70    6   12    1.40   17.25      0.6758E+01  0.2921E+01 "alien"
   17    9  112    1.39   17.25      0.6756E+01  0.3719E+01 "alien"
   38   24   92    1.40   17.24      0.6755E+01  0.3232E+01 "alien"
    7   67   72    1.39   17.24      0.6754E+01  0.2734E+01 "alien"
    9   85    2    1.40   17.23      0.6749E+01  0.3324E+01 "alien"
   38    6   95    1.42   17.20      0.5595E+01  0.2609E+01 "alien"
   11   37  104    1.38   17.19      0.6735E+01  0.5061E+01 "alien"
    7   77   46    1.41   17.19      0.5593E+01  0.2352E+01 "alien"
   36   66   49    1.37   17.18      0.6729E+01  0.5196E+01 "alien"
   59   43   14    1.42   17.16      0.5582E+01  0.2297E+01 "alien"
   11   79   44    1.38   17.13      0.6712E+01  0.4800E+01 "alien"
    4   48   97    1.38   17.13      0.6709E+01  0.5196E+01 "alien"
   32   42   86    1.40   17.12      0.6708E+01  0.3559E+01 "alien"
   11   71   62    1.40   17.12      0.6708E+01  0.2713E+01 "alien"
   39   27   90    1.39   17.11      0.6705E+01  0.3887E+01 "alien"
    9   25  109    1.40   17.10      0.6697E+01  0.2783E+01 "alien"
   27   79    3    1.40   17.09      0.6695E+01  0.4876E+01 "alien"
   34   56   70    1.38   17.09      0.6693E+01  0.5493E+01 "alien"
   22   12  108    1.40   17.07      0.6688E+01  0.3062E+01 "alien"
   52   34   60    1.42   17.03      0.5540E+01  0.2915E+01 "alien"
   65    3   46    1.39   17.02      0.6668E+01  0.3014E+01 "alien"
   14   14  113    1.38   17.02      0.6666E+01  0.5547E+01 "alien"
   35    7   99    1.41   17.01      0.6663E+01  0.3797E+01 "alien"
   29   55   70    1.44   17.01      0.5534E+01  0.2058E+01 "alien"
   53   33   61    1.40   17.00      0.6659E+01  0.3783E+01 "alien"
   52   22   74    1.38   17.00      0.6658E+01  0.4145E+01 "alien"
   40   44   74    1.40   16.97      0.6649E+01  0.2904E+01 "alien"
   54   34   61    1.38   16.95      0.6640E+01  0.5682E+01 "alien"
   20   80   28    1.39   16.95      0.6639E+01  0.3325E+01 "alien"
   11   83   20    1.40   16.93      0.6634E+01  0.2620E+01 "alien"
   50   58    9    1.42   16.92      0.5505E+01  0.3150E+01 "alien"
   40   70   17    1.39   16.91      0.6625E+01  0.5019E+01 "alien"
   52   44   52    1.39   16.91      0.6624E+01  0.5290E+01 "alien"
   33   15  102    1.38   16.88      0.6613E+01  0.5996E+01 "alien"
   40   62   47    1.39   16.88      0.6612E+01  0.5313E+01 "alien"
   30   78    3    1.39   16.87      0.6609E+01  0.3300E+01 "alien"
   23   39   96    1.40   16.85      0.6602E+01  0.2989E+01 "alien"
   58   30   53    1.39   16.84      0.6599E+01  0.3913E+01 "alien"
   39   69   29    1.38   16.82      0.6587E+01  0.5240E+01 "alien"
    8   14  114    1.39   16.80      0.6582E+01  0.5193E+01 "alien"
   45   53   49    1.42   16.79      0.5464E+01  0.2868E+01 "alien"
   26   34   99    1.38   16.78      0.6575E+01  0.3550E+01 "alien"
   49   51   47    1.40   16.78      0.6572E+01  0.4858E+01 "alien"
   38   50   68    1.41   16.77      0.5456E+01  0.3621E+01 "alien"
   31   45   86    1.38   16.76      0.6567E+01  0.3749E+01 "alien"
   12   66   72    1.39   16.75      0.6561E+01  0.2614E+01 "alien"
   10   36  102    1.41   16.75      0.5449E+01  0.2267E+01 "alien"
   67    9   36    1.39   16.74      0.6558E+01  0.3023E+01 "alien"
   26    8  107    1.40   16.69      0.6540E+01  0.3497E+01 "alien"
   44   36   74    1.41   16.69      0.5429E+01  0.2275E+01 "alien"
   44   44   69    1.39   16.69      0.6536E+01  0.4494E+01 "alien"
   63   31   35    1.38   16.65      0.6522E+01  0.5603E+01 "alien"
   64    2   51    1.38   16.65      0.6522E+01  0.3318E+01 "alien"
   42    8   94    1.38   16.64      0.6521E+01  0.6408E+01 "alien"
   41   53   61    1.40   16.64      0.6519E+01  0.3090E+01 "alien"
   54   22   66    1.41   16.63      0.5412E+01  0.2604E+01 "alien"
   44   64   29    1.39   16.62      0.6511E+01  0.4850E+01 "alien"
    8   42  101    1.39   16.62      0.6511E+01  0.4364E+01 "alien"
   41    1   94    1.40   16.62      0.6509E+01  0.4055E+01 "alien"
    2   36  106    1.38   16.61      0.6506E+01  0.3171E+01 "alien"
   13   83   21    1.39   16.59      0.6500E+01  0.3130E+01 "alien"
   36   60   60    1.38   16.56      0.6489E+01  0.5243E+01 "alien"
   12   34  105    1.39   16.55      0.6484E+01  0.5127E+01 "alien"
   46   62   21    1.41   16.55      0.6484E+01  0.3540E+01 "alien"
   12   32  105    1.40   16.55      0.6483E+01  0.4658E+01 "alien"
    2   20  114    1.38   16.55      0.6482E+01  0.3341E+01 "alien"
   39   67   37    1.38   16.54      0.6480E+01  0.4858E+01 "alien"
   47   23   82    1.38   16.52      0.6472E+01  0.4105E+01 "alien"
    2   42  101    1.39   16.51      0.6467E+01  0.3389E+01 "alien"
   65   13   36    1.42   16.48      0.5362E+01  0.2189E+01 "alien"
   56   14   62    1.44   16.47      0.5358E+01  0.1691E+01 "alien"
   37   11   96    1.41   16.45      0.5352E+01  0.2293E+01 "alien"
   61   29   42    1.40   16.45      0.6443E+01  0.3855E+01 "alien"
   66   14   40    1.38   16.43      0.6438E+01  0.3962E+01 "alien"
   68   20   25    1.38   16.42      0.6434E+01  0.5354E+01 "alien"
    3   77   46    1.42   16.40      0.5337E+01  0.2710E+01 "alien"
    7   83   30    1.39   16.39      0.6422E+01  0.4632E+01 "alien"


 List of    500 reflections *NOT* obeying Wilson distribution (sorted by resolution)
 Ice rings could occur at (Angstrom):
 3.897,3.669,3.441, 2.671,2.249,2.072, 1.948,1.918,1.883,1.721

   h    k    l     RES        Z       Intensity    Sigma

   32   44   87    1.37   25.69      0.1006E+02  0.5878E+01
   31   47   85    1.37   29.23      0.1145E+02  0.5578E+01
   37   57   65    1.37   20.98      0.8219E+01  0.5439E+01
   36   66   49    1.37   17.18      0.6729E+01  0.5196E+01
   36   56   68    1.37   17.31      0.6781E+01  0.5444E+01
   33   53   76    1.37   22.21      0.8700E+01  0.5723E+01
   65   17   44    1.37   19.58      0.7671E+01  0.6066E+01
   19   35  103    1.37   18.14      0.7107E+01  0.5583E+01
   22   34  102    1.37   29.02      0.1137E+02  0.5298E+01
   17   71   62    1.37   21.26      0.8330E+01  0.4723E+01
   40   62   50    1.37   18.77      0.7354E+01  0.5064E+01
   26   52   84    1.38   24.32      0.9529E+01  0.5325E+01
   32   56   73    1.38   18.02      0.7059E+01  0.5294E+01
   18   34  104    1.38   32.17      0.1260E+02  0.5258E+01
   14   46   97    1.38   20.90      0.8189E+01  0.5495E+01
    7   67   74    1.38   18.63      0.7297E+01  0.4966E+01
   64   10   51    1.38   28.43      0.1114E+02  0.5788E+01
   14    4  115    1.38   24.47      0.9585E+01  0.5564E+01
   68   20   25    1.38   16.42      0.6434E+01  0.5354E+01
   40   60   54    1.38   17.73      0.6944E+01  0.5217E+01
   35   63   57    1.38   20.02      0.7845E+01  0.5054E+01
   28   78   24    1.38   22.54      0.8830E+01  0.4818E+01
   26   64   67    1.38   26.01      0.1019E+02  0.6093E+01
   26   80   17    1.38   34.65      0.1357E+02  0.4887E+01
    4   20  114    1.38   18.47      0.7236E+01  0.4778E+01
   50   32   72    1.38   22.81      0.8938E+01  0.6278E+01
   10   20  113    1.38   23.22      0.9098E+01  0.5014E+01
   23   53   85    1.38   19.56      0.7662E+01  0.4885E+01
    7   31  109    1.38   20.96      0.8213E+01  0.5284E+01
   33   63   60    1.38   18.48      0.7238E+01  0.5162E+01
   40   66   39    1.38   26.18      0.1026E+02  0.5459E+01
   28   52   82    1.38   30.72      0.1204E+02  0.5416E+01
   14    2  115    1.38   19.90      0.7798E+01  0.3934E+01
   17   57   84    1.38   19.92      0.7803E+01  0.5564E+01
   22   28  105    1.38   22.74      0.8907E+01  0.5281E+01
    8   14  115    1.38   17.47      0.6844E+01  0.3733E+01
   11   27  110    1.38   19.28      0.7552E+01  0.4778E+01
    5   25  112    1.38   17.55      0.6877E+01  0.4942E+01
   35   19   99    1.38   17.87      0.7001E+01  0.5386E+01
   33   77    4    1.38   20.04      0.7852E+01  0.3535E+01
   18   28  107    1.38   20.79      0.8146E+01  0.5333E+01
   15    9  114    1.38   20.05      0.7853E+01  0.5488E+01
   20   52   88    1.38   20.21      0.7915E+01  0.3977E+01
   12   18  113    1.38   37.20      0.1457E+02  0.5555E+01
    4   74   61    1.38   18.69      0.7323E+01  0.5063E+01
   19   69   64    1.38   18.32      0.7177E+01  0.4825E+01
   30   34   96    1.38   17.99      0.7049E+01  0.4969E+01
   41   71    6    1.38   18.66      0.7311E+01  0.3439E+01
   35   53   73    1.38   18.25      0.7151E+01  0.5395E+01
   33   15  102    1.38   16.88      0.6613E+01  0.5996E+01
   13   23  111    1.38   21.84      0.8555E+01  0.5022E+01
   19   29  106    1.38   25.03      0.9806E+01  0.5076E+01
   63   25   44    1.38   24.68      0.9668E+01  0.6416E+01
    2   20  114    1.38   16.55      0.6482E+01  0.3341E+01
   51   33   69    1.38   21.81      0.8545E+01  0.6515E+01
   30   58   72    1.38   18.20      0.7130E+01  0.5424E+01
   21    1  112    1.38   20.60      0.8071E+01  0.5693E+01
   51   19   78    1.38   21.22      0.8313E+01  0.3901E+01
   15   21  111    1.38   18.94      0.7420E+01  0.5060E+01
   67    9   39    1.38   38.84      0.1521E+02  0.5294E+01
   68   20   24    1.38   18.25      0.7149E+01  0.3831E+01
   66   20   36    1.38   34.34      0.1345E+02  0.5412E+01
   65   31   25    1.38   18.42      0.7215E+01  0.5606E+01
   26   68   59    1.38   34.92      0.1368E+02  0.5622E+01
   26   34   99    1.38   16.78      0.6575E+01  0.3550E+01
   69    9   28    1.38   27.05      0.1060E+02  0.5033E+01
   70    4   23    1.38   17.37      0.6806E+01  0.5404E+01
   34   56   70    1.38   17.09      0.6693E+01  0.5493E+01
   46   16   87    1.38   18.28      0.7163E+01  0.4368E+01
   15   81   34    1.38   24.10      0.9440E+01  0.4676E+01
   12   44   99    1.38   17.75      0.6955E+01  0.5399E+01
   29   11  106    1.38   23.09      0.9046E+01  0.5606E+01
   34   76    9    1.38   18.27      0.7156E+01  0.3413E+01
   71    7    9    1.38   26.82      0.1051E+02  0.5761E+01
   60   26   53    1.38   17.38      0.6808E+01  0.5906E+01
   19   81   28    1.38   18.39      0.7204E+01  0.4674E+01
   39   67   38    1.38   20.96      0.8210E+01  0.5097E+01
   57   25   62    1.38   19.48      0.7632E+01  0.5646E+01
   36   58   64    1.38   26.82      0.1051E+02  0.5458E+01
   33   67   51    1.38   18.14      0.7108E+01  0.4861E+01
   44   34   80    1.38   20.80      0.8147E+01  0.5086E+01
   26   60   73    1.38   21.39      0.8380E+01  0.5329E+01
   20   62   75    1.38   32.51      0.1274E+02  0.5210E+01
   59   27   55    1.38   23.77      0.9314E+01  0.6187E+01
   34   48   80    1.38   28.23      0.1106E+02  0.5484E+01
   68   26    7    1.38   22.25      0.8716E+01  0.3669E+01
   33   31   95    1.38   27.40      0.1074E+02  0.4898E+01
   18   82   24    1.38   17.75      0.6954E+01  0.4912E+01
    5   31  109    1.38   20.73      0.8123E+01  0.4659E+01
   28   14  106    1.38   28.15      0.1103E+02  0.5838E+01
   17   77   46    1.38   23.50      0.9205E+01  0.4912E+01
   35   21   98    1.38   24.09      0.9436E+01  0.5981E+01
   61   11   59    1.38   18.34      0.7184E+01  0.3713E+01
   40   10   96    1.38   20.60      0.8071E+01  0.6201E+01
   71    7    8    1.38   24.75      0.9695E+01  0.5279E+01
   13   25  110    1.38   34.44      0.1349E+02  0.5387E+01
   37   15   98    1.38   23.66      0.9270E+01  0.5932E+01
   42    8   94    1.38   16.64      0.6521E+01  0.6408E+01
   20   82   19    1.38   17.41      0.6821E+01  0.4576E+01
   70   14   13    1.38   20.49      0.8028E+01  0.5216E+01
    3   57   88    1.38   23.85      0.9342E+01  0.5053E+01
   15   83   23    1.38   23.57      0.9235E+01  0.5218E+01
   52   10   79    1.38   17.36      0.6801E+01  0.4970E+01
   38   18   96    1.38   25.08      0.9824E+01  0.5789E+01
   37   65   48    1.38   17.41      0.6820E+01  0.5059E+01
    3   67   74    1.38   19.24      0.7538E+01  0.3363E+01
   15   73   58    1.38   18.19      0.7125E+01  0.4660E+01
   29   65   61    1.38   18.81      0.7370E+01  0.4921E+01
   70    8   20    1.38   28.39      0.1112E+02  0.5263E+01
   40   14   95    1.38   23.05      0.9029E+01  0.6073E+01
   71    3   11    1.38   18.07      0.7081E+01  0.5111E+01
   64   26   38    1.38   22.26      0.8719E+01  0.5665E+01
   59   23   58    1.38   21.82      0.8547E+01  0.6441E+01
   31   67   54    1.38   29.55      0.1157E+02  0.4958E+01
   32   68   50    1.38   19.35      0.7579E+01  0.4834E+01
   40   58   57    1.38   30.82      0.1207E+02  0.5502E+01
   65   31   24    1.38   20.42      0.7998E+01  0.5355E+01
   70    4   22    1.38   18.73      0.7337E+01  0.4985E+01
   33   61   63    1.38   25.11      0.9835E+01  0.5373E+01
   53    5   78    1.38   30.94      0.1212E+02  0.5255E+01
   15   17  112    1.38   27.20      0.1066E+02  0.3523E+01
    6   52   93    1.38   18.75      0.7345E+01  0.4626E+01
   34   76    6    1.38   22.38      0.8768E+01  0.5071E+01
   31   45   86    1.38   16.76      0.6567E+01  0.3749E+01
   68   22   19    1.38   22.22      0.8705E+01  0.3778E+01
   22   64   70    1.38   20.41      0.7995E+01  0.5513E+01
   56   30   60    1.38   22.61      0.8857E+01  0.5775E+01
   34   14  101    1.38   21.67      0.8488E+01  0.5611E+01
   47   27   80    1.38   18.65      0.7304E+01  0.3952E+01
   54   34   61    1.38   16.95      0.6640E+01  0.5682E+01
   66   14   40    1.38   16.43      0.6438E+01  0.3962E+01
    5   49   96    1.38   23.92      0.9371E+01  0.5714E+01
   38   42   81    1.38   18.35      0.7187E+01  0.5099E+01
   18   82   23    1.38   19.07      0.7469E+01  0.4706E+01
   33   17  101    1.38   18.12      0.7097E+01  0.5643E+01
   30   70   48    1.38   21.65      0.8480E+01  0.4879E+01
    9   47   97    1.38   18.11      0.7096E+01  0.4692E+01
   14   14  113    1.38   17.02      0.6666E+01  0.5547E+01
    4   48   97    1.38   17.13      0.6709E+01  0.5196E+01
   32   56   72    1.38   17.52      0.6862E+01  0.5388E+01
   42   12   93    1.38   29.05      0.1138E+02  0.6381E+01
   31   35   94    1.38   22.77      0.8920E+01  0.4900E+01
   42   64   38    1.38   26.52      0.1039E+02  0.5130E+01
   71    7    4    1.38   20.69      0.8104E+01  0.3560E+01
   44   36   78    1.38   22.28      0.8729E+01  0.5206E+01
   53    3   78    1.38   20.39      0.7988E+01  0.5361E+01
   36   60   60    1.38   16.56      0.6489E+01  0.5243E+01
   22   80   26    1.38   19.42      0.7610E+01  0.3470E+01
   48   24   80    1.38   26.50      0.1038E+02  0.4024E+01
   63   31   35    1.38   16.65      0.6522E+01  0.5603E+01
   28   70   51    1.38   44.12      0.1728E+02  0.5254E+01
   36   70   35    1.38   20.72      0.8118E+01  0.4737E+01
   39   67   37    1.38   16.54      0.6480E+01  0.4858E+01
   11   79   44    1.38   17.13      0.6712E+01  0.4800E+01
   11   37  104    1.38   17.19      0.6735E+01  0.5061E+01
   70   10   17    1.38   18.32      0.7178E+01  0.3488E+01
   46    4   89    1.38   17.47      0.6843E+01  0.6690E+01
   71    7    1    1.38   18.21      0.7132E+01  0.3545E+01
   52   18   76    1.38   19.30      0.7562E+01  0.4014E+01
   36   66   47    1.38   17.99      0.7048E+01  0.4675E+01
   14   32  106    1.38   19.42      0.7609E+01  0.4808E+01
   29   23  102    1.38   24.75      0.9696E+01  0.5518E+01
   33   59   66    1.38   37.84      0.1482E+02  0.5405E+01
    6   58   86    1.38   18.65      0.7307E+01  0.4975E+01
   47   23   82    1.38   16.52      0.6472E+01  0.4105E+01
   52   22   74    1.38   17.00      0.6658E+01  0.4145E+01
    9   81   38    1.38   24.72      0.9682E+01  0.4930E+01
   63    9   53    1.38   20.51      0.8034E+01  0.3202E+01
   31   71   43    1.38   18.32      0.7177E+01  0.4999E+01
   35   17   99    1.38   35.46      0.1389E+02  0.5833E+01
   32   70   44    1.38   24.77      0.9702E+01  0.4838E+01
   48    4   86    1.38   28.25      0.1107E+02  0.7251E+01
   47   37   72    1.38   21.19      0.8303E+01  0.5042E+01
   67   27   15    1.38   21.56      0.8446E+01  0.3835E+01
   64    2   51    1.38   16.65      0.6522E+01  0.3318E+01
   37   43   81    1.38   36.00      0.1410E+02  0.5159E+01
    2   36  106    1.38   16.61      0.6506E+01  0.3171E+01
   51   11   80    1.38   17.48      0.6848E+01  0.4078E+01
   39   57   60    1.38   37.18      0.1457E+02  0.5562E+01
   39   69   29    1.38   16.82      0.6587E+01  0.5240E+01
   42   60   48    1.38   23.46      0.9189E+01  0.5267E+01
   16   40  100    1.39   21.47      0.8409E+01  0.5376E+01
   38   68   36    1.39   21.66      0.8484E+01  0.5081E+01
   41   63   43    1.39   20.01      0.7838E+01  0.5197E+01
   10   44   99    1.39   24.42      0.9568E+01  0.5554E+01
    8   22  112    1.39   17.83      0.6983E+01  0.3469E+01
   13    9  114    1.39   17.47      0.6843E+01  0.5323E+01
   56   36   53    1.39   17.57      0.6884E+01  0.5635E+01
   38   70   28    1.39   40.91      0.1603E+02  0.5312E+01
   58   30   54    1.39   23.48      0.9199E+01  0.5653E+01
   63   27   40    1.39   19.83      0.7768E+01  0.5423E+01
   31   33   95    1.39   23.23      0.9102E+01  0.4891E+01
   11   41  101    1.39   22.53      0.8828E+01  0.4821E+01
    7   83   30    1.39   16.39      0.6422E+01  0.4632E+01
    8   42  101    1.39   16.62      0.6511E+01  0.4364E+01
   18   34  103    1.39   19.17      0.7511E+01  0.5312E+01
   36   30   92    1.39   24.27      0.9506E+01  0.5201E+01
   45    5   90    1.39   22.38      0.8767E+01  0.6891E+01
   24   28  103    1.39   23.26      0.9114E+01  0.4913E+01
   24   60   74    1.39   30.79      0.1206E+02  0.3771E+01
   21   79   32    1.39   19.37      0.7589E+01  0.3331E+01
   16   26  108    1.39   22.23      0.8710E+01  0.3848E+01
   40   54   63    1.39   25.47      0.9977E+01  0.5542E+01
   39   19   94    1.39   17.71      0.6939E+01  0.4052E+01
   38   24   93    1.39   21.47      0.8411E+01  0.4046E+01
   38   60   56    1.39   18.53      0.7259E+01  0.5392E+01
   17   81   29    1.39   22.74      0.8908E+01  0.4752E+01
   34   16  100    1.39   22.06      0.8640E+01  0.6175E+01
   42   34   82    1.39   27.69      0.1085E+02  0.4976E+01
   39   55   63    1.39   27.53      0.1078E+02  0.5449E+01
   24   14  108    1.39   23.01      0.9014E+01  0.3981E+01
   43   65   30    1.39   19.15      0.7500E+01  0.4554E+01
    7   47   97    1.39   23.00      0.9012E+01  0.5119E+01
   60   32   45    1.39   26.40      0.1034E+02  0.5835E+01
   23   29  103    1.39   21.03      0.8240E+01  0.5349E+01
   42   14   92    1.39   25.39      0.9945E+01  0.5348E+01
   65   29   26    1.39   17.80      0.6972E+01  0.5437E+01
   30   70   47    1.39   23.68      0.9276E+01  0.4979E+01
   56   38   50    1.39   21.47      0.8409E+01  0.5932E+01
   45    3   90    1.39   20.84      0.8166E+01  0.4647E+01
   54   26   67    1.39   18.42      0.7217E+01  0.4185E+01
   68   24    9    1.39   22.57      0.8840E+01  0.3666E+01
   33   61   62    1.39   25.90      0.1015E+02  0.5477E+01
   55   27   64    1.39   23.15      0.9070E+01  0.4103E+01
   22   30  103    1.39   28.45      0.1115E+02  0.5547E+01
   38    6   98    1.39   31.77      0.1245E+02  0.4442E+01
   69   19   10    1.39   29.30      0.1148E+02  0.5246E+01
   36   64   51    1.39   19.67      0.7705E+01  0.4852E+01
   43   19   89    1.39   28.26      0.1107E+02  0.4145E+01
   52   40   58    1.39   22.53      0.8824E+01  0.5193E+01
   65   31   21    1.39   17.99      0.7049E+01  0.5677E+01
   20   26  106    1.39   17.99      0.7047E+01  0.4703E+01
   32   18  101    1.39   21.86      0.8562E+01  0.4220E+01
   32   54   74    1.39   21.34      0.8360E+01  0.3828E+01
   28   64   63    1.39   18.33      0.7180E+01  0.3826E+01
   41   67   29    1.39   26.87      0.1052E+02  0.5017E+01
   40   66   36    1.39   23.21      0.9094E+01  0.5164E+01
   50   20   78    1.39   17.55      0.6877E+01  0.4273E+01
    4   84   25    1.39   20.84      0.8164E+01  0.4963E+01
   48   46   59    1.39   17.49      0.6851E+01  0.5173E+01
   26   34   98    1.39   18.32      0.7179E+01  0.3424E+01
    8   14  114    1.39   16.80      0.6582E+01  0.5193E+01
   69   15   18    1.39   22.42      0.8782E+01  0.3811E+01
   20   80   28    1.39   16.95      0.6639E+01  0.3325E+01
   30   78    4    1.39   21.96      0.8602E+01  0.3361E+01
   59   35   44    1.39   18.85      0.7385E+01  0.5703E+01
   23   37   98    1.39   22.29      0.8733E+01  0.3690E+01
   58   22   60    1.39   19.35      0.7579E+01  0.3689E+01
   17   77   44    1.39   28.76      0.1127E+02  0.5007E+01
   12   34  105    1.39   16.55      0.6484E+01  0.5127E+01
   40   70   17    1.39   16.91      0.6625E+01  0.5019E+01
   59   25   55    1.39   20.29      0.7950E+01  0.3863E+01
   30   78    3    1.39   16.87      0.6609E+01  0.3300E+01
   61   37   32    1.39   20.33      0.7964E+01  0.5342E+01
   18   60   78    1.39   18.51      0.7252E+01  0.3784E+01
   39   27   90    1.39   17.11      0.6705E+01  0.3887E+01
   40   62   47    1.39   16.88      0.6612E+01  0.5313E+01
   61   31   42    1.39   22.27      0.8722E+01  0.3784E+01
   64   34   20    1.39   20.28      0.7945E+01  0.5456E+01
   41   55   59    1.39   24.39      0.9553E+01  0.4069E+01
   12   66   72    1.39   16.75      0.6561E+01  0.2614E+01
   44   64   29    1.39   16.62      0.6511E+01  0.4850E+01
   25   21  105    1.39   35.02      0.1372E+02  0.5487E+01
   21   57   80    1.39   22.00      0.8617E+01  0.3672E+01
   40   10   95    1.39   24.33      0.9533E+01  0.4264E+01
   68   10   30    1.39   27.91      0.1093E+02  0.3062E+01
   65   33   13    1.39   34.34      0.1345E+02  0.5745E+01
   67    9   36    1.39   16.74      0.6558E+01  0.3023E+01
   17   83   13    1.39   17.69      0.6929E+01  0.3299E+01
   27   61   69    1.39   26.18      0.1026E+02  0.3898E+01
   57   21   63    1.39   22.60      0.8852E+01  0.5092E+01
   43   23   87    1.39   22.70      0.8892E+01  0.4221E+01
   20   82   13    1.39   17.38      0.6808E+01  0.3249E+01
    7   67   72    1.39   17.24      0.6754E+01  0.2734E+01
   52   44   52    1.39   16.91      0.6624E+01  0.5290E+01
   24   72   50    1.39   22.96      0.8996E+01  0.3042E+01
    1   45   99    1.39   30.40      0.1191E+02  0.4963E+01
   44   52   58    1.39   27.21      0.1066E+02  0.5372E+01
   39   69   27    1.39   21.94      0.8595E+01  0.4888E+01
   44   44   69    1.39   16.69      0.6536E+01  0.4494E+01
    6   50   94    1.39   17.91      0.7014E+01  0.2797E+01
   12   32  106    1.39   22.88      0.8962E+01  0.4563E+01
   62   30   39    1.39   17.34      0.6791E+01  0.3829E+01
   14   84   10    1.39   17.37      0.6804E+01  0.3107E+01
   58   30   53    1.39   16.84      0.6599E+01  0.3913E+01
   37   61   55    1.39   26.75      0.1048E+02  0.5156E+01
   65    3   46    1.39   17.02      0.6668E+01  0.3014E+01
   50   32   70    1.39   30.10      0.1179E+02  0.4160E+01
   37   35   87    1.39   24.98      0.9786E+01  0.4706E+01
   14   10  113    1.39   19.02      0.7450E+01  0.3669E+01
   45   53   54    1.39   17.94      0.7027E+01  0.5624E+01
   43   67   18    1.39   23.33      0.9141E+01  0.4905E+01
   16   82   23    1.39   18.97      0.7433E+01  0.4608E+01
   33   57   68    1.39   18.69      0.7323E+01  0.5572E+01
   40   28   88    1.39   28.99      0.1136E+02  0.4033E+01
   34   68   44    1.39   19.10      0.7483E+01  0.4840E+01
   62    8   55    1.39   21.99      0.8615E+01  0.3041E+01
   69    1   26    1.39   18.62      0.7296E+01  0.2537E+01
   17    9  112    1.39   17.25      0.6756E+01  0.3719E+01
   57   25   60    1.39   27.03      0.1059E+02  0.4101E+01
   44   32   80    1.39   25.51      0.9992E+01  0.4108E+01
    4   70   67    1.39   19.61      0.7681E+01  0.2891E+01
   44   38   75    1.39   28.11      0.1101E+02  0.5043E+01
   15   75   51    1.39   18.60      0.7288E+01  0.2773E+01
   44   42   71    1.39   17.71      0.6937E+01  0.4849E+01
   46   22   83    1.39   18.73      0.7336E+01  0.4069E+01
   66   20   32    1.39   17.26      0.6762E+01  0.3038E+01
   68    2   32    1.39   19.69      0.7712E+01  0.2576E+01
   13   83   21    1.39   16.59      0.6500E+01  0.3130E+01
    3   19  113    1.39   18.77      0.7355E+01  0.4919E+01
   39    9   96    1.39   21.76      0.8523E+01  0.6255E+01
    9    1  115    1.39   21.25      0.8325E+01  0.3719E+01
   39   55   62    1.39   20.63      0.8081E+01  0.3713E+01
   48   44   61    1.39   28.43      0.1114E+02  0.5051E+01
   25   13  107    1.39   33.64      0.1318E+02  0.3942E+01
   55   43   44    1.39   22.04      0.8633E+01  0.5177E+01
   38   52   68    1.39   19.50      0.7638E+01  0.4201E+01
   56   30   58    1.39   23.44      0.9182E+01  0.3912E+01
   66   24   26    1.39   17.44      0.6833E+01  0.3161E+01
    2   42  101    1.39   16.51      0.6467E+01  0.3389E+01
   50   16   79    1.39   17.40      0.6815E+01  0.3560E+01
   26   58   74    1.39   19.17      0.7512E+01  0.5055E+01
   28   76   28    1.39   18.41      0.7212E+01  0.3308E+01
   34   40   86    1.39   18.71      0.7329E+01  0.3901E+01
   57   33   52    1.39   21.51      0.8426E+01  0.3870E+01
   51   47   49    1.39   18.01      0.7056E+01  0.4890E+01
   57   23   61    1.39   21.04      0.8243E+01  0.4088E+01
   63    5   52    1.39   17.31      0.6780E+01  0.2662E+01
   23   39   96    1.40   16.85      0.6602E+01  0.2989E+01
   60   26   50    1.40   27.02      0.1059E+02  0.6059E+01
   64   34   17    1.40   21.44      0.8398E+01  0.3777E+01
   49   51   47    1.40   16.78      0.6572E+01  0.4858E+01
   24   72   49    1.40   23.31      0.9131E+01  0.2860E+01
   14   84    3    1.40   22.13      0.8671E+01  0.4851E+01
   48   28   76    1.40   17.31      0.6780E+01  0.3888E+01
   38   24   92    1.40   17.24      0.6755E+01  0.3232E+01
   67   27    2    1.40   17.26      0.6762E+01  0.4017E+01
   32   50   78    1.40   22.28      0.8728E+01  0.3793E+01
   41   45   72    1.40   17.91      0.7018E+01  0.5006E+01
   23   59   75    1.40   19.91      0.7801E+01  0.3615E+01
    9   85    2    1.40   17.23      0.6749E+01  0.3324E+01
   40    6   95    1.40   18.41      0.7212E+01  0.4197E+01
   60    8   60    1.40   17.69      0.6930E+01  0.2790E+01
   40   36   82    1.40   17.42      0.6823E+01  0.4832E+01
   26    8  107    1.40   16.69      0.6540E+01  0.3497E+01
   37   67   39    1.40   26.28      0.1030E+02  0.5196E+01
   27   47   86    1.40   19.98      0.7826E+01  0.5024E+01
   16   58   81    1.40   18.88      0.7395E+01  0.3451E+01
    4   76   53    1.40   18.26      0.7155E+01  0.2832E+01
   45   61   34    1.40   21.80      0.8540E+01  0.3433E+01
   70    6   12    1.40   17.25      0.6758E+01  0.2921E+01
   45   53   53    1.40   17.30      0.6779E+01  0.5229E+01
   12   22  110    1.40   30.18      0.1182E+02  0.3803E+01
   24   78   27    1.40   17.42      0.6824E+01  0.3349E+01
   17   25  107    1.40   24.18      0.9474E+01  0.3147E+01
   32   42   86    1.40   17.12      0.6708E+01  0.3559E+01
   28   46   86    1.40   25.01      0.9799E+01  0.4936E+01
   47   53   48    1.40   17.45      0.6836E+01  0.4928E+01
   11   71   62    1.40   17.12      0.6708E+01  0.2713E+01
   41   53   61    1.40   16.64      0.6519E+01  0.3090E+01
   10   84   15    1.40   17.45      0.6834E+01  0.3524E+01
   41    1   94    1.40   16.62      0.6509E+01  0.4055E+01
   36   12   98    1.40   22.14      0.8672E+01  0.4061E+01
   50   32   69    1.40   19.19      0.7520E+01  0.3060E+01
   27   79    3    1.40   17.09      0.6695E+01  0.4876E+01
   46   58   39    1.40   22.59      0.8851E+01  0.3654E+01
   53   47   42    1.40   26.77      0.1049E+02  0.4961E+01
   46   56   44    1.40   20.99      0.8223E+01  0.5521E+01
   11   33  105    1.40   26.45      0.1036E+02  0.4554E+01
   18   76   44    1.40   19.12      0.7490E+01  0.3358E+01
   11    1  114    1.40   18.62      0.7296E+01  0.3600E+01
   43   67   13    1.40   19.44      0.7616E+01  0.3363E+01
   55   23   65    1.40   20.05      0.7856E+01  0.3970E+01
   34   34   90    1.40   17.70      0.6935E+01  0.2638E+01
   26   42   91    1.40   17.84      0.6990E+01  0.2541E+01
   32   14  101    1.40   24.73      0.9687E+01  0.5982E+01
   40   44   74    1.40   16.97      0.6649E+01  0.2904E+01
   14    2  113    1.40   18.14      0.7107E+01  0.3731E+01
   49   43   59    1.40   20.03      0.7846E+01  0.4754E+01
   51   41   57    1.40   21.30      0.8346E+01  0.3668E+01
   28   56   74    1.40   23.01      0.9014E+01  0.3757E+01
   31   13  102    1.40   17.42      0.6822E+01  0.5523E+01
   61   29   42    1.40   16.45      0.6443E+01  0.3855E+01
   27   13  105    1.40   17.88      0.7004E+01  0.3062E+01
    5   33  106    1.40   18.96      0.7426E+01  0.3168E+01
   12   84    6    1.40   19.79      0.7753E+01  0.3327E+01
   44   46   65    1.40   39.45      0.1545E+02  0.5151E+01
   11   83   20    1.40   16.93      0.6634E+01  0.2620E+01
   19   51   87    1.40   18.98      0.7437E+01  0.2896E+01
   12   32  105    1.40   16.55      0.6483E+01  0.4658E+01
   26   60   70    1.40   23.15      0.9068E+01  0.3671E+01
   31   57   69    1.40   18.81      0.7367E+01  0.3953E+01
   47   53   47    1.40   22.75      0.8914E+01  0.5127E+01
   27   71   46    1.40   18.36      0.7193E+01  0.2503E+01
   24   54   80    1.40   18.60      0.7288E+01  0.3584E+01
   62   40    4    1.40   24.99      0.9790E+01  0.4631E+01
   53   47   41    1.40   18.08      0.7083E+01  0.4829E+01
   53   33   61    1.40   17.00      0.6659E+01  0.3783E+01
   59   43   23    1.40   17.77      0.6963E+01  0.5049E+01
   30   64   58    1.40   23.84      0.9339E+01  0.3901E+01
   48   50   50    1.40   22.95      0.8991E+01  0.5126E+01
    4   22  111    1.40   19.10      0.7484E+01  0.3307E+01
   35    9   99    1.40   18.66      0.7310E+01  0.3979E+01
    9   25  109    1.40   17.10      0.6697E+01  0.2783E+01
   42   60   44    1.40   17.73      0.6945E+01  0.3040E+01
   57   41   38    1.40   21.57      0.8452E+01  0.2978E+01
   37    9   97    1.40   24.94      0.9768E+01  0.5893E+01
   22   12  108    1.40   17.07      0.6688E+01  0.3062E+01
    2   42  100    1.40   18.71      0.7330E+01  0.4603E+01
   26   18  104    1.40   24.34      0.9535E+01  0.3819E+01
   50   56   28    1.41   23.78      0.9315E+01  0.5467E+01
   33   41   85    1.41   19.45      0.7620E+01  0.3204E+01
    8   50   92    1.41   20.16      0.7899E+01  0.2484E+01
   47   17   82    1.41   19.17      0.7509E+01  0.2875E+01
   34   54   69    1.41   17.60      0.6894E+01  0.3852E+01
   35    7   99    1.41   17.01      0.6663E+01  0.3797E+01
   23   13  107    1.41   19.78      0.7749E+01  0.3101E+01
   55   43   41    1.41   20.60      0.8070E+01  0.2938E+01
    4   34  105    1.41   19.25      0.7543E+01  0.3240E+01
   25   79   10    1.41   20.08      0.7865E+01  0.4822E+01
   52   52   31    1.41   29.23      0.1145E+02  0.5049E+01
   40    2   94    1.41   28.78      0.1128E+02  0.4055E+01
   40   58   52    1.41   19.40      0.7598E+01  0.3060E+01
   37    5   97    1.41   30.22      0.1184E+02  0.4189E+01
   46   62   21    1.41   16.55      0.6484E+01  0.3540E+01
   51   47   46    1.41   36.95      0.1447E+02  0.4942E+01
   45   57   42    1.41   18.33      0.7181E+01  0.3527E+01
   50   50   43    1.41   17.38      0.5654E+01  0.4796E+01
   60   40   23    1.41   19.38      0.6307E+01  0.2866E+01
   20   38   97    1.41   17.80      0.5792E+01  0.2224E+01
   37   11   96    1.41   16.45      0.5352E+01  0.2293E+01
   49   41   60    1.41   19.94      0.6486E+01  0.2919E+01
   22   44   91    1.41   19.40      0.6314E+01  0.2289E+01
   39   45   73    1.41   17.62      0.5732E+01  0.2928E+01
   20   68   60    1.41   21.27      0.6921E+01  0.2890E+01
   27   55   75    1.41   23.69      0.7708E+01  0.3160E+01
   20   14  108    1.41   21.70      0.7060E+01  0.2303E+01
   29   59   67    1.41   17.43      0.5671E+01  0.3829E+01
   62   14   49    1.41   17.80      0.5793E+01  0.2405E+01
   57   31   51    1.41   17.35      0.5644E+01  0.2945E+01
   40   50   65    1.41   21.27      0.6922E+01  0.3070E+01
   57   47   18    1.41   27.32      0.8890E+01  0.4569E+01
   12   18  110    1.41   20.01      0.6510E+01  0.2230E+01
    5   33  105    1.41   17.46      0.5681E+01  0.2878E+01
   38   56   59    1.41   25.17      0.8191E+01  0.3190E+01
   30   60   64    1.41   19.21      0.6252E+01  0.3664E+01
   27    7  105    1.41   18.44      0.6001E+01  0.3159E+01
   54   22   66    1.41   16.63      0.5412E+01  0.2604E+01
    4   70   64    1.41   17.27      0.5618E+01  0.2435E+01
   39    9   94    1.41   24.07      0.7832E+01  0.2366E+01
   54   50   26    1.41   28.30      0.9209E+01  0.4853E+01
    9   23  109    1.41   24.99      0.8132E+01  0.2854E+01
   38   50   68    1.41   16.77      0.5456E+01  0.3621E+01
   46   44   62    1.41   17.85      0.5809E+01  0.2234E+01
    7   77   46    1.41   17.19      0.5593E+01  0.2352E+01
   27   77   17    1.41   23.36      0.7602E+01  0.2219E+01
   47   37   68    1.41   24.31      0.7911E+01  0.3986E+01
   12   30  105    1.41   20.33      0.6614E+01  0.2865E+01
   46   50   53    1.41   20.07      0.6531E+01  0.2981E+01
   50   28   70    1.41   24.18      0.7866E+01  0.2694E+01
   38   60   51    1.41   20.23      0.6583E+01  0.2987E+01
   44   36   74    1.41   16.69      0.5429E+01  0.2275E+01
   37   55   62    1.41   17.32      0.5634E+01  0.2938E+01
   10   36  102    1.41   16.75      0.5449E+01  0.2267E+01
   51   55   23    1.42   17.97      0.5847E+01  0.5287E+01
   53   39   52    1.42   20.74      0.6749E+01  0.2913E+01
   35   73    4    1.42   18.47      0.6010E+01  0.2495E+01
   69    9    9    1.42   17.59      0.5725E+01  0.2183E+01
   42   50   61    1.42   27.18      0.8843E+01  0.2981E+01
   10   82   22    1.42   22.92      0.7457E+01  0.2281E+01
   14   50   89    1.42   19.41      0.6315E+01  0.2094E+01
   56   36   47    1.42   26.39      0.8586E+01  0.3139E+01
   29   75   22    1.42   17.34      0.5641E+01  0.2128E+01
   67    9   28    1.42   19.50      0.6344E+01  0.2501E+01
   61   37   22    1.42   21.35      0.6947E+01  0.2232E+01
   52   34   60    1.42   17.03      0.5540E+01  0.2915E+01
   38    6   95    1.42   17.20      0.5595E+01  0.2609E+01
   24   66   59    1.42   18.27      0.5944E+01  0.2181E+01
   37   57   58    1.42   31.13      0.1013E+02  0.3235E+01
   45   53   49    1.42   16.79      0.5464E+01  0.2868E+01
   65   13   36    1.42   16.48      0.5362E+01  0.2189E+01
   16   82    2    1.42   20.63      0.6711E+01  0.2691E+01
    3   77   46    1.42   16.40      0.5337E+01  0.2710E+01
   55   47   28    1.42   21.43      0.6973E+01  0.2915E+01
   50   58    9    1.42   16.92      0.5505E+01  0.3150E+01
   59   43   14    1.42   17.16      0.5582E+01  0.2297E+01
   58   24   53    1.42   18.21      0.5925E+01  0.1953E+01
   17   41   95    1.42   17.29      0.5627E+01  0.1760E+01
   39   69    9    1.43   19.11      0.6217E+01  0.2461E+01
   45   37   70    1.43   17.34      0.5643E+01  0.1691E+01
   56   48   14    1.43   18.84      0.6130E+01  0.2143E+01
   59   41   19    1.43   18.74      0.6097E+01  0.2063E+01
   53   53    9    1.43   21.48      0.6989E+01  0.2939E+01
   29   55   70    1.44   17.01      0.5534E+01  0.2058E+01
   22   68   54    1.44   19.01      0.6186E+01  0.1616E+01
   56   14   62    1.44   16.47      0.5358E+01  0.1691E+01
   44   56   41    1.44   17.48      0.5687E+01  0.2168E+01
   58   44    5    1.44   18.90      0.6150E+01  0.2244E+01
   50   56    4    1.45   23.05      0.7498E+01  0.2522E+01
   46   60    1    1.46   19.25      0.6545E+01  0.2442E+01

 NUMBER OF UNIQUE ALIEN REFLECTIONS WITH A Z-SCORE ABOVE LIMIT       245
 (ALIENS ABOVE LIMIT (REJECT_ALIEN=      20.0) ARE MARKED INVALID)

 NUMBER OF REFLECTION RECORDS ON OUTPUT FILE "XDS_ASCII.HKL"     2436793
 NUMBER OF ACCEPTED OBSERVATIONS (INCLUDING SYSTEMATIC ABSENCES) 2421931
 NUMBER OF REJECTED MISFITS & ALIENS (marked by -1*SIGMA(IOBS))    14862


 cpu time used                179.5 sec
 elapsed wall-clock time      143.5 sec
