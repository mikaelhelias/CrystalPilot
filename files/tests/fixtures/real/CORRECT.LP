
 ***** CORRECT ***** (VERSION Apr 16, 2026  BUILT=20260616)   5-Sep-2026

 INPUT PARAMETER VALUES
 ----------------------
 SPACE_GROUP_NUMBER=   20 as used in the INTEGRATE step
 UNIT_CELL_CONSTANTS=    98.195   119.525   161.027  90.000  90.000  90.000 as used by INTEGRATE
 FRIEDEL'S_LAW=TRUE 
 PROFILE_FITTING= TRUE 
 OVERLOAD=     29991     MINPK=  75.00000    WFAC1=   1.0
 INCLUDE_RESOLUTION_RANGE=    20.000     0.000
 NAME_TEMPLATE_OF_DATA_FRAMES=/data/xtal_1/xtal_1_??????.h5
 DATA_RANGE=       1      60
 ROTATION_AXIS=  1.000000  0.000000  0.000000
 OSCILLATION_RANGE=  0.200000
 STARTING_ANGLE=     5.885     STARTING_FRAME=       1
 X-RAY_WAVELENGTH=  0.979338
 INCIDENT_BEAM_DIRECTION= -0.002531 -0.001792  0.999995
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
 REFLECTING_RANGE_E.S.D.=   0.134
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

   79478 REFLECTIONS ON FILE "INTEGRATE.HKL"
       0 CORRUPTED REFLECTION RECORDS (IGNORED)
       0 MATCHING REFLECTIONS SPECIFIED IN FILE "FILTER.HKL"
       0 REFLECTIONS INCOMPLETE OR OUTSIDE IMAGE RANGE       1 ...      60
       0 OVERLOADED REFLECTIONS (IGNORED)
       0 REFLECTIONS OUTSIDE ACCEPTED RESOLUTION RANGES
                OR TOO CLOSE TO ROTATION AXIS (IGNORED)
   79478 REFLECTIONS ACCEPTED



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
 NUMBER OF ACCEPTED REFLECTIONS FOR CALCULATING Rmeas             1680
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

 *  44        aP          0.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
 *  31        aP          0.0      77.3   77.3  161.0  90.0  90.0  78.8    1  1  0  0 -1  1  0  0  0  0  2  0
 *  14        mC          0.0      98.2  119.5  161.0  90.0  90.0  90.0    2  0  0  0  0 -2  0  0  0  0 -2  0
 *  34        mP          0.0      77.3  161.0   77.3  90.0 101.2  90.0   -1 -1  0  0  0  0  2  0 -1  1  0  0
 *  13        oC          0.0      98.2  119.5  161.0  90.0  90.0  90.0    2  0  0  0  0 -2  0  0  0  0 -2  0
 *  10        mC          0.0     119.5   98.2  161.0  90.0  90.0  90.0    0  2  0  0  2  0  0  0  0  0 -2  0
    33        mP         97.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
    35        mP         97.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
    32        oP         97.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
    11        tP         97.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
    39        mC        153.0     159.0   77.3  161.0  90.0  90.0  72.7    3  1  0  0  1 -1  0  0  0  0 -2  0
    29        mC        153.0      77.3  159.0  161.0  90.0  90.0  72.7    1  1  0  0  3 -1  0  0  0  0 -2  0
    38        oC        153.0      77.3  159.0  161.0  90.0  90.0 107.3   -1 -1  0  0  3 -1  0  0  0  0  2  0
    12        hP        153.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
    28        mC        298.5      77.3  331.2   77.3  92.6 101.2  76.5   -1 -1  0  0 -1 -1  4  0 -1  1  0  0
    30        mC        298.5      77.3  331.2   77.3  92.6 101.2  76.5   -1  1  0  0 -1  1 -4  0 -1 -1  0  0
    37        mC        347.0     331.2   77.3   77.3 101.2  92.6  76.5    1  1 -4  0  1  1  0  0  1 -1  0  0
    36        oC        347.0      77.3  331.2   77.3  87.4 101.2 103.5    1  1  0  0 -1 -1  4  0  1 -1  0  0
    41        mC        347.0     331.2   77.3   77.3 101.2  92.6  76.5    1  1 -4  0  1  1  0  0  1 -1  0  0
    40        oC        347.0      77.3  331.2   77.3  87.4 101.2 103.5    1  1  0  0 -1 -1  4  0  1 -1  0  0
    27        mC        500.0     159.0   77.3  178.6  85.2 112.4  72.7   -3 -1  0  0 -1  1  0  0  1  1 -2  0
    15        tI        597.0      77.3   77.3  336.7  79.3  79.3 101.2    1  1  0  0  1 -1  0  0  2  0 -4  0
    42        oI        597.0      77.3   77.3  336.7 100.7 100.7 101.2   -1 -1  0  0 -1  1  0  0  2  0 -4  0
    26        oF        625.0      77.3  159.0  331.2  86.0 103.5 107.3    1 -1  0  0 -3 -1  0  0 -1  1 -4  0
     9        hR        750.0      77.3   98.2  497.6  90.0 100.7 129.4    1 -1  0  0 -2  0  0  0  0  2 -6  0
     1        cF        999.0     188.6  200.5  188.6 133.3  62.8 133.3    2  0 -2  0  0 -2  2  0 -2  0 -2  0
     2        hR        999.0      98.2  178.6  200.5 121.6  90.0 106.0    2  0  0  0 -1 -1  2  0  0 -2 -2  0
     3        cP        999.0      77.3   77.3  161.0  90.0  90.0 101.2    1  1  0  0  1 -1  0  0  0  0 -2  0
     5        cI        999.0     178.6   98.2  178.6  74.0  39.1  74.0    1  1 -2  0  2  0  0  0  1 -1 -2  0
     4        hR        999.0     119.5  178.6  188.6 128.8  90.0 109.5    0  2  0  0 -1 -1 -2  0 -2  0  2  0
     6        tI        999.0     178.6  178.6   98.2  74.0  74.0  39.1    1 -1 -2  0  1  1 -2  0  2  0  0  0
     7        tI        999.0     178.6   98.2  178.6  74.0  39.1  74.0    1  1 -2  0  2  0  0  0  1 -1 -2  0
     8        oI        999.0      98.2  178.6  178.6  39.1  74.0  74.0   -2  0  0  0 -1 -1  2  0 -1  1  2  0
    16        oF        999.0      98.2  119.5  336.7  90.0 107.0  90.0   -2  0  0  0  0  2  0  0  2  0 -4  0
    17        mC        999.0     119.5   98.2  178.6  74.0 109.5  90.0    0  2  0  0 -2  0  0  0 -1 -1  2  0
    18        tI        999.0     178.6  188.6   77.3  70.7  94.8 128.8    1  1 -2  0  2  0  2  0  1 -1  0  0
    19        oI        999.0      77.3  178.6  188.6  51.2  70.7  85.2   -1  1  0  0  1  1 -2  0 -2  0 -2  0
    20        mC        999.0     178.6  178.6   77.3  94.8  94.8 128.7   -1  1  2  0 -1  1 -2  0 -1 -1  0  0
    21        tP        999.0      77.3  161.0   77.3  90.0 101.2  90.0   -1 -1  0  0  0  0  2  0 -1  1  0  0
    22        hP        999.0      77.3  161.0   77.3  90.0 101.2  90.0   -1 -1  0  0  0  0  2  0 -1  1  0  0
    23        oC        999.0     178.6  178.6   77.3  85.2  94.8  51.3   -1 -1  2  0  1  1  2  0 -1  1  0  0
    24        hR        999.0     226.3  178.6   77.3  85.2  77.9  68.0    3 -1 -2  0 -1  1 -2  0  1  1  0  0
    25        mC        999.0     178.6  178.6   77.3  85.2  94.8  51.3    1 -1 -2  0 -1  1 -2  0  1  1  0  0
    43        mI        999.0      98.2  336.7   77.3 100.7 129.4  73.0   -2  0  0  0 -2  0  4  0  1  1  0  0

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

  *   0.00        0    4.4     347    0.01  2  0  0  0  0  2  0  0  0  0  2  0

 ************ SELECTED SPACE GROUP AND UNIT CELL FOR THIS DATA SET ************

 SPACE_GROUP_NUMBER=   20
 UNIT_CELL_CONSTANTS=    99.00   120.00   161.00  90.000  90.000  90.000
 UNIT_CELL_A-AXIS=    59.343    77.485    10.808
 UNIT_CELL_B-AXIS=   -90.035    62.260    47.997
 UNIT_CELL_C-AXIS=    41.793   -52.429   146.405
 REFLECTIONS H,K,L FROM "INTEGRATE.HKL" WILL BE REINDEXED BY
 H' = (  2*H +  0*K +  0*L)/ 2 +  0
 K' = (  0*H +  2*K +  0*L)/ 2 +  0
 L' = (  0*H +  0*K +  2*L)/ 2 +  0

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


 REFINED VALUES OF DIFFRACTION PARAMETERS DERIVED FROM     18557 INDEXED SPOTS
 REFINED PARAMETERS:   POSITION BEAM  ORIENTATION CELL
 STANDARD DEVIATION OF SPOT    POSITION (PIXELS)     0.45
 STANDARD DEVIATION OF SPINDLE POSITION (DEGREES)    0.05
 SPACE GROUP NUMBER     20
 UNIT CELL PARAMETERS     98.312   119.672   161.236  90.000  90.000  90.000
 E.S.D. OF CELL PARAMETERS  7.6E-02 4.9E-02 1.1E-01 0.0E+00 0.0E+00 0.0E+00
 REC. CELL PARAMETERS   0.010172  0.008356  0.006202  90.000  90.000  90.000
 COORDINATES OF UNIT CELL A-AXIS    59.421    77.577    10.782
 COORDINATES OF UNIT CELL B-AXIS   -90.131    62.358    48.054
 COORDINATES OF UNIT CELL C-AXIS    41.875   -52.450   146.603
 CRYSTAL MOSAICITY (DEGREES)     0.134
 LAB COORDINATES OF ROTATION AXIS  1.000000  0.000000  0.000000
 DIRECT BEAM COORDINATES (REC. ANGSTROEM)  -0.001094 -0.001714  1.021096
 DETECTOR COORDINATES (PIXELS) OF DIRECT BEAM    2002.12   2248.36
 DETECTOR ORIGIN (PIXELS) AT                     2004.94   2252.79
 CRYSTAL TO DETECTOR DISTANCE (mm)       197.74
 LAB COORDINATES OF DETECTOR X-AXIS  1.000000  0.000000  0.000000
 LAB COORDINATES OF DETECTOR Y-AXIS  0.000000  1.000000  0.000000


 THE DATA COLLECTION STATISTICS REPORTED BELOW ASSUMES:
 SPACE_GROUP_NUMBER=   20
 UNIT_CELL_CONSTANTS=    98.31   119.67   161.24  90.000  90.000  90.000


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
 -0.05  0.05      7865         34.958       0.944
  0.05  0.15      7929         33.778       0.977
  0.15  0.25      7947         35.877       0.920
  0.25  0.35      7969         31.147       1.060
  0.35  0.45      7966         32.101       1.028
  0.45  0.55      8071         30.309       1.089
  0.55  0.65      7954         31.323       1.054
  0.65  0.75      7923         33.673       0.980
  0.75  0.85      8007         32.069       1.029
  0.85  0.95      7847         34.978       0.944

 -0.05  0.95     79478         33.011       1.000


 ******************************************************************************
           CORRECTION FACTORS AS FUNCTION OF IMAGE NUMBER & RESOLUTION
 ******************************************************************************

 RECIPROCAL CORRECTION FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     

 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW= TRUE
 TOTAL NUMBER OF CORRECTION FACTORS DEFINED        2
 DEGREES OF FREEDOM OF CHI^2 FIT              5562.0
 CHI^2-VALUE OF FIT OF CORRECTION FACTORS      0.820
 NUMBER OF CYCLES CARRIED OUT                      3

 CORRECTION FACTORS for visual inspection by XDS-Viewer DECAY.cbf           
 XMIN=     0.3 XMAX=    59.6 NXBIN=    1
 YMIN= 0.00252 YMAX= 0.53060 NYBIN=    2
 NUMBER OF REFLECTIONS USED FOR DETERMINING CORRECTION FACTORS      11110


 ******************************************************************************
  CORRECTION FACTORS AS FUNCTION OF X (fast) & Y(slow) IN THE DETECTOR PLANE
 ******************************************************************************

 RECIPROCAL CORRECTION FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     

 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW= TRUE
 TOTAL NUMBER OF CORRECTION FACTORS DEFINED        2
 DEGREES OF FREEDOM OF CHI^2 FIT              5562.0
 CHI^2-VALUE OF FIT OF CORRECTION FACTORS      0.820
 NUMBER OF CYCLES CARRIED OUT                      3

 CORRECTION FACTORS for visual inspection by XDS-Viewer MODPIX.cbf          
 XMIN=     6.3 XMAX=  4142.7 NXBIN=    1
 YMIN=     5.9 YMAX=  4363.3 NYBIN=    2
 NUMBER OF REFLECTIONS USED FOR DETERMINING CORRECTION FACTORS      11110


 ******************************************************************************
   CORRECTION FACTORS AS FUNCTION OF IMAGE NUMBER & DETECTOR SURFACE POSITION
 ******************************************************************************

 RECIPROCAL CORRECTION FACTORS FOR INPUT DATA SETS MERGED TO
 OUTPUT FILE: XDS_ASCII.HKL                                     

 THE CALCULATIONS ASSUME         FRIEDEL'S_LAW= TRUE
 TOTAL NUMBER OF CORRECTION FACTORS DEFINED       13
 DEGREES OF FREEDOM OF CHI^2 FIT              5562.0
 CHI^2-VALUE OF FIT OF CORRECTION FACTORS      0.815
 NUMBER OF CYCLES CARRIED OUT                      3

 CORRECTION FACTORS for visual inspection by XDS-Viewer ABSORP.cbf          
 XMIN=     0.3 XMAX=    59.6 NXBIN=    1
 DETECTOR_SURFACE_POSITION=    2075    2185
 DETECTOR_SURFACE_POSITION=    2777    2925
 DETECTOR_SURFACE_POSITION=    1372    2925
 DETECTOR_SURFACE_POSITION=    1372    1445
 DETECTOR_SURFACE_POSITION=    2777    1445
 DETECTOR_SURFACE_POSITION=    3664    2878
 DETECTOR_SURFACE_POSITION=    2733    3859
 DETECTOR_SURFACE_POSITION=    1416    3859
 DETECTOR_SURFACE_POSITION=     485    2878
 DETECTOR_SURFACE_POSITION=     485    1491
 DETECTOR_SURFACE_POSITION=    1416     510
 DETECTOR_SURFACE_POSITION=    2733     510
 DETECTOR_SURFACE_POSITION=    3664    1491
 NUMBER OF REFLECTIONS USED FOR DETERMINING CORRECTION FACTORS      11110


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
 6.553E-01  2.307E-03   25.72


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

   19.916  11.321    23.94   1.31      2.48      2.31      84     135       3
   11.321   8.743    22.82   1.22      2.33      2.28      91     188       3
    8.743   7.379    20.93   1.36      3.11      2.42     107     242       8
    7.379   6.503    19.97   1.27      2.21      2.43     113     273       4
    6.503   5.880    19.56   1.24      3.16      2.53     119     304      13
    5.880   5.407    19.23   1.44      2.90      2.43     125     352       8
    5.407   5.032    19.33   1.61      2.74      2.49     112     326       4
    5.032   4.726    19.81   1.17      2.53      2.42     108     379       4
    4.726   4.470    19.92   1.26      2.27      2.44      98     382      12
    4.470   4.251    20.01   1.38      2.58      2.41     110     402      10
    4.251   4.062    19.30   1.04      2.10      2.39      96     390       4
    4.062   3.896    17.36   1.49      3.37      2.65      96     423      14
    3.896   3.748    16.65   1.29      2.99      2.74     112     486       6
    3.748   3.617    16.28   1.25      2.87      2.79     112     494       4
    3.617   3.498    15.58   1.06      3.06      2.99     122     517      10
    3.498   3.390    14.47   1.21      3.16      2.99     124     528      20
    3.390   3.292    12.92   1.45      4.05      3.24     146     564       8
    3.292   3.201    12.29   1.40      4.01      3.61     144     581      10
    3.201   3.118    11.31   1.02      4.53      4.15     162     595       8
    3.118   3.041    10.05   1.03      4.21      4.36     164     634       6
    3.041   2.969     9.26   0.93      4.22      4.36     156     626      10
    2.969   2.903     8.77   1.38      6.71      5.21     170     654       4
    2.903   2.840     7.60   1.08      6.35      6.14     197     681       6
    2.840   2.781     6.81   1.39      8.36      6.89     169     682      10
    2.781   2.726     6.21   1.07      9.12      8.42     181     682       6
    2.726   2.674     5.39   0.99      9.90      9.62     209     728       7
    2.674   2.625     5.17   0.95      9.30     10.16     220     690       0
    2.625   2.579     4.92   1.13     11.32     10.29     217     656       6
    2.579   2.535     4.75   1.07     10.66     10.11     213     695       0
    2.535   2.493     4.16   1.28     14.25     13.05     223     742       5
    2.493   2.453     3.86   1.13     11.58     11.11     183     725       5
    2.453   2.415     3.50   1.05     15.76     15.15     235     778       6
    2.415   2.378     3.32   0.91     14.50     14.65     207     720       5
    2.378   2.344     2.90   0.89     23.96     25.74     154     687       4
    2.344   2.310     2.75   1.05     19.63     18.54     207     765       6
    2.310   2.278     2.83   0.95     16.14     16.45     217     744       6
    2.278   2.248     2.41   1.02     24.21     23.06     271     801       4
    2.248   2.218     2.14   0.74     21.98     25.71     271     797       0
    2.218   2.190     2.03   1.18     33.65     29.29     252     797      10
    2.190   2.163     1.82   0.90     30.67     32.27     315     893       2
    2.163   2.137     1.74   1.07     32.25     30.62     220     800       2
    2.137   2.111     1.40   0.98     42.81     42.52     315     901       2
    2.111   2.087     1.42   1.09     41.22     38.14     276     869       6
    2.087   2.063     1.18   1.07     48.11     45.83     317     904       8
    2.063   2.041     1.17   1.09     52.79     51.43     304     886       2
    2.041   2.019     1.19   0.87     44.56     46.01     289     914       2
    2.019   1.997     0.98   1.02     55.36     55.05     304     932       4
    1.997   1.976     0.88   1.07     78.34     75.04     322     937       0
    1.976   1.956     0.77   1.02     79.37     78.18     327     952       2
    1.956   1.937     0.67   0.94     67.74     70.38     311     940       4
    1.937   1.918     0.64   0.96     94.81     95.63     334     995       4
    1.918   1.900     0.63   0.92    110.12    110.75     326     966       0
    1.900   1.882     0.60   0.86     92.74     98.54     345    1001       4
    1.882   1.864     0.52   1.05    117.11    117.09     354    1017       0
    1.864   1.848     0.45   0.87    111.63    118.76     349    1003       4
    1.848   1.831     0.47   0.88    128.13    132.90     353     988       2
    1.831   1.815     0.42   0.85    123.75    132.17     358     953       2
    1.815   1.800     0.28   0.97    194.22    190.26     341     940       4
    1.800   1.784     0.37   0.88    163.45    172.62     341     985       2
    1.784   1.770     0.25   0.90    220.61    231.26     344    1028       0
    1.770   1.755     0.31   0.98    188.98    187.73     276     961       4
    1.755   1.741     0.17   0.73    385.10    437.66     370    1105       4
    1.741   1.727     0.24   0.79    179.64    194.68     237     965       4
    1.727   1.714     0.22   1.13    378.18    348.22     307    1020       4
    1.714   1.701     0.20   0.73    226.06    263.70     239     949       2
    1.701   1.688     0.23   0.89    222.15    232.39     358    1042       0
    1.688   1.675     0.20   0.81    304.12    341.94     284    1008       4
    1.675   1.663     0.14   0.87    259.51    280.84     318    1077       0
    1.663   1.651     0.13   0.98    298.36    301.93     344    1073       3
    1.651   1.639     0.17   0.87    207.89    219.39     294    1049       4
    1.639   1.628     0.14   1.08    264.04    250.26     365    1158       0
    1.628   1.616     0.11   0.89    382.38    406.72     293    1088       2
    1.616   1.605     0.09   0.89    477.35    493.57     340    1120       3
    1.605   1.595     0.13   0.88    211.98    221.86     326    1141       2
    1.595   1.584     0.12   0.83    544.21    571.47     311    1112       0
    1.584   1.574     0.07   0.92    599.56    621.52     338    1164       2
    1.574   1.563     0.13   0.90    554.55    576.49     300    1173       0
    1.563   1.553     0.06   0.91    747.36    776.40     324    1172       0
    1.553   1.544     0.12   0.81    278.09    305.79     329    1192       4
    1.544   1.534     0.12   0.99    515.70    513.90     260    1184       2
    1.534   1.525     0.11   0.93    403.62    413.17     328    1211       4
    1.525   1.515     0.09   0.90    469.12    493.49     286    1156       2
    1.515   1.506     0.06   1.07    643.86    608.17     312    1229       0
    1.506   1.497     0.05   0.78    544.76    599.57     282    1197       2
    1.497   1.488     0.06   0.92   2558.17   2664.91     298    1197       2
    1.488   1.480     0.06   0.79    883.22    970.76     293    1220       0
    1.480   1.471     0.05   1.04   1382.01   1327.24     270    1148       2
    1.471   1.463     0.02   0.79   1408.45   1522.96     244    1048       2
    1.463   1.455    -0.04   0.72   4664.30   5281.94     250     984       2
    1.455   1.447     0.02   0.85   3930.07   4320.46     217     904       2
    1.447   1.439     0.00   0.87    -99.90    -99.90     194     817       2
    1.439   1.431     0.05   0.93   3335.18   3396.37     190     789       0
    1.431   1.423     0.07   0.92    390.47    419.99     154     725       4
    1.423   1.416     0.04   0.94   1088.49   1111.70     120     645       0
    1.416   1.408     0.06   0.67    -99.90    -99.90      70     418       0
    1.408   1.401     0.13   0.69    399.45    463.93      46     341       0
    1.401   1.394     0.14   0.41    446.89    589.35      12     260       0
    1.394   1.387     0.08   0.00    -99.90    -99.90       0     190       0
    1.387   1.380     0.10   0.00    -99.90    -99.90       0     142       0
    1.380   1.373    -0.14   0.00    -99.90    -99.90       0      72       0
   --------------------------------------------------------------------------
   19.916   1.373     2.74   0.98      8.93      8.85   22821   79095     383



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
  STATISTICS OF SAVED DATA SET "XDS_ASCII.HKL" (DATA_RANGE=       1      60)
 FILE TYPE:         XDS_ASCII      MERGE=FALSE          FRIEDEL'S_LAW=TRUE 
 ******************************************************************************

   REFLECTIONS OF TYPE H,0,0  0,K,0  0,0,L OR EXPECTED TO BE ABSENT (*)
   --------------------------------------------------------------------

   H    K    L  RESOLUTION  INTENSITY     SIGMA    INTENSITY/SIGMA  #OBSERVED

   40    0    0     2.458   0.2855E+02  0.4848E+01         5.89           1 
   42    0    0     2.341   0.6459E+02  0.6818E+01         9.47           1 
   44    0    0     2.234   0.1280E+03  0.9202E+01        13.91           1 
   46    0    0     2.137   0.1180E+01  0.4568E+01         0.26           1 
   48    0    0     2.048   0.2319E+02  0.5752E+01         4.03           1 
   50    0    0     1.966   0.3886E+01  0.4654E+01         0.84           1 
   52    0    0     1.891   0.8319E+01  0.4821E+01         1.73           1 
   54    0    0     1.821   0.1163E+01  0.4181E+01         0.28           1 
   56    0    0     1.756   0.3755E+01  0.4330E+01         0.87           1 
   58    0    0     1.695   0.1154E+02  0.4986E+01         2.32           1 
   60    0    0     1.639  -0.3655E+00  0.4548E+01        -0.08           1 
   62    0    0     1.586   0.1028E+02  0.4749E+01         2.16           1 
   64    0    0     1.536  -0.4506E+01  0.4083E+01        -1.10           1 
   66    0    0     1.490   0.2223E+01  0.4481E+01         0.50           1 
   68    0    0     1.446  -0.2666E+01  0.4292E+01        -0.62           1 

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

     4.04        3426    2828      8073       35.0%       2.5%      2.4%     1177   21.70      3.6%    99.8*     0    0.000       0
     2.89        6198    5431     13637       39.8%       3.7%      3.4%     1533   13.36      5.3%    99.6*     0    0.000       0
     2.37        7876    6703     17413       38.5%      10.5%     10.0%     2275    5.29     14.6%    97.6*     0    0.000       0
     2.05        9070    7552     20435       37.0%      29.4%     28.8%     2858    2.12     40.4%    83.5*   -36    0.726      10
     1.84       10736    8811     23088       38.2%      76.8%     78.0%     3658    0.81    106.1%    45.5*     0    0.789      26
     1.68       11036    9199     25455       36.1%     209.7%    218.8%     3518    0.29    290.8%    10.9*   -17    0.450      42
     1.56       12399   10538     27645       38.1%     331.0%    344.0%     3566    0.13    458.9%     2.3     24    0.739      23
     1.46       12930   11296     29594       38.2%     623.4%    647.9%     3209    0.07    872.7%     1.5     76    0.706       2
     1.37        5393    4882     31514       15.5%    4315.4%   4629.7%     1021    0.05   6099.8%     6.7      0    0.000       0
    total       79064   67240    196854       34.2%       8.9%      8.9%    22815    2.94     12.4%    99.8*    -1    0.632     103


 NUMBER OF REFLECTIONS IN SELECTED SUBSET OF IMAGES     79478
 NUMBER OF REJECTED MISFITS                               383
 NUMBER OF SYSTEMATIC ABSENT REFLECTIONS                    0
 NUMBER OF ACCEPTED OBSERVATIONS                        79095
 NUMBER OF UNIQUE ACCEPTED REFLECTIONS                  67268



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

   WILSON LINE (using all data) : A=   5.207 B=  31.538 CORRELATION=  0.97
      #      RES      SS        <I>       log(<I>)       BO
     951     7.259   0.005  1.9080E+02       5.251      -4.6
    1661     4.725   0.011  1.8434E+02       5.217      -0.4
    2242     3.710   0.018  1.2468E+02       4.826      10.5
    2743     3.158   0.025  5.5108E+01       4.009      23.9
    3113     2.797   0.032  2.2032E+01       3.092      33.1
    3148     2.533   0.039  1.1657E+01       2.456      35.3
    3333     2.336   0.046  7.3453E+00       1.994      35.1
    3631     2.176   0.053  4.5818E+00       1.522      34.9
    3920     2.046   0.060  2.7847E+00       1.024      35.0
    4163     1.937   0.067  1.6147E+00       0.479      35.5
    4216     1.844   0.074  9.9242E-01      -0.008      35.5
    4435     1.761   0.081  5.8647E-01      -0.534      35.6
    4554     1.690   0.088  4.2099E-01      -0.865      34.7
    4915     1.627   0.094  2.9166E-01      -1.232      34.1
    5230     1.570   0.101  2.5288E-01      -1.375      32.4
    5488     1.519   0.108  2.3044E-01      -1.468      30.8
    5082     1.474   0.115  1.1901E-01      -2.129      31.9
    3342     1.432   0.122  1.6712E-01      -1.789      28.7
    1073     1.396   0.128  2.4573E-01      -1.404      25.8


 HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF  CENTRIC DATA
    AS COMPARED WITH THEORETICAL VALUES. (EXPECTED: 1.00)    
      #      RES        <I**2>/      <I**3>/      <I**4>/  
                         3<I>**2     15<I>**3    105<I>**4 

      94     7.259      0.64654      0.53954      0.39607    
     108     4.725      0.64462      0.41039      0.21815    
      98     3.710       1.2046       1.2904       1.3144    
     103     3.158       2.2578       3.2667       4.2873    
     105     2.797      0.99293      0.89999      0.71437    
      93     2.533      0.77853      0.68598      0.53902    
      95     2.336      0.67532      0.42793      0.24096    
      96     2.176       1.2084       1.1034      0.92678    
      82     2.046      0.93730      0.70191      0.52819    
      76     1.937       1.5773       1.7128       2.0320    
      88     1.844       2.2848       2.1732       2.6273    
      81     1.761       5.3860       2.9338       6.9812    
      91     1.690       8.8736       11.681       32.702    
      90     1.627       20.822       40.401       176.12    
      97     1.570       25.332       33.600       145.78    
      85     1.474       118.10       162.16       3222.8    
      75     1.432       41.659       83.680       434.99    
    1669   overall       14.181       16.551       224.04    


 HIGHER ORDER MOMENTS OF WILSON DISTRIBUTION OF ACENTRIC DATA
    AS COMPARED WITH THEORETICAL VALUES. (EXPECTED: 1.00)    
      #      RES        <I**2>/      <I**3>/      <I**4>/  
                         2<I>**2      6<I>**3     24<I>**4 

     857     7.259       1.3162       1.8743       2.7195    
    1553     4.725       1.1160       1.3977       2.0008    
    2144     3.710       1.0918       1.3263       1.7398    
    2640     3.158       1.1602       1.5067       2.0358    
    3008     2.797       1.1263       1.3845       1.7982    
    3055     2.533       1.1349       1.6214       3.7016    
    3238     2.336       1.1704       1.5460       2.5464    
    3535     2.176       1.2097       1.4934       2.1911    
    3838     2.046       1.3981       1.5982       1.9787    
    4087     1.937       2.0159       2.2973       3.1832    
    4128     1.844       3.2815       3.7003       6.7519    
    4354     1.761       6.9501       8.1794       29.538    
    4463     1.690       12.822       14.272       95.560    
    4825     1.627       26.499       28.752       420.00    
    5133     1.570       35.204       47.703       724.70    
    5389     1.519       45.965       61.279       1173.9    
    4997     1.474       182.76       374.65       19822.    
    3267     1.432       83.785       162.59       4054.5    
    1060     1.396       39.939       53.940       786.08    
   65571   overall       29.333       50.852       1919.3    

   ======= CUMULATIVE INTENSITY DISTRIBUTION =======
 DEFINITIONS:
   <I>    = mean reflection intensity
 Na(Z)exp = expected number of acentric reflections with I <= Z*<I>
 Na(Z)obs = observed number of acentric reflections with I <= Z*<I>
 Nc(Z)exp = expected number of  centric reflections with I <= Z*<I>
 Nc(Z)obs = observed number of  centric reflections with I <= Z*<I>



 Nc(Z)obs/Nc(Z)exp versus resolution and Z (0.1-1.0)
      #      RES     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0

      94     7.259  1.07  1.05  1.15  1.12  1.12  1.14  1.16  1.17  1.18  1.17
     108     4.725  1.01  1.10  1.18  1.15  1.12  1.12  1.12  1.09  1.06  1.05
      98     3.710  0.78  0.65  0.78  0.86  0.86  0.91  0.92  0.94  0.95  0.94
     103     3.158  0.78  0.93  0.91  0.96  0.97  0.95  0.94  0.91  0.92  0.92
     105     2.797  0.88  0.96  1.05  1.03  1.06  1.02  1.00  1.02  0.97  1.02
      93     2.533  0.82  0.84  0.98  1.00  0.97  0.94  1.01  1.01  1.03  1.06
      95     2.336  0.89  0.82  0.86  0.80  0.87  0.92  0.95  0.95  0.98  1.02
      96     2.176  0.88  0.84  0.83  0.86  0.78  0.84  0.85  0.88  0.87  0.89
      82     2.046  1.18  0.88  0.88  0.88  0.84  0.85  0.82  0.85  0.91  0.91
      76     1.937  1.64  1.22  1.07  1.00  0.99  0.94  0.97  0.94  0.92  0.91
      88     1.844  1.60  1.31  1.17  1.08  1.05  0.99  0.93  0.92  0.90  0.88
      81     1.761  1.49  1.11  1.01  0.94  0.85  0.79  0.74  0.73  0.71  0.69
      91     1.690  1.90  1.37  1.16  1.05  0.95  0.92  0.87  0.84  0.80  0.77
      90     1.627  1.48  1.06  0.88  0.77  0.73  0.67  0.65  0.64  0.61  0.59
      97     1.570  1.66  1.19  1.01  0.89  0.81  0.77  0.73  0.72  0.69  0.66
      85     1.474  1.71  1.23  1.02  0.90  0.81  0.75  0.71  0.67  0.64  0.64
      75     1.432  1.83  1.31  1.09  0.96  0.87  0.81  0.78  0.74  0.71  0.68
    1669   overall  1.16  0.97  0.93  0.89  0.86  0.85  0.84  0.83  0.82  0.82


 Na(Z)obs/Na(Z)exp versus resolution and Z (0.1-1.0)
      #      RES     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0

     857     7.259  1.25  1.24  1.16  1.20  1.16  1.14  1.11  1.09  1.05  1.02
    1553     4.725  1.04  1.08  1.05  1.05  1.03  1.01  1.01  1.01  1.02  1.02
    2144     3.710  1.15  1.11  1.13  1.07  1.05  1.03  1.04  1.03  1.02  1.02
    2640     3.158  1.23  1.25  1.25  1.22  1.17  1.13  1.11  1.08  1.07  1.05
    3008     2.797  1.09  1.11  1.09  1.10  1.07  1.05  1.05  1.05  1.04  1.03
    3055     2.533  1.23  1.06  1.02  1.03  1.03  1.02  1.03  1.03  1.03  1.02
    3238     2.336  1.58  1.12  1.03  1.00  1.00  1.00  0.99  1.00  1.00  1.00
    3535     2.176  1.97  1.28  1.08  0.98  0.96  0.95  0.95  0.95  0.96  0.96
    3838     2.046  2.50  1.52  1.21  1.04  0.98  0.95  0.91  0.89  0.90  0.90
    4087     1.937  3.20  1.81  1.36  1.14  1.03  0.96  0.91  0.89  0.87  0.85
    4128     1.844  3.76  2.07  1.51  1.24  1.08  0.99  0.92  0.87  0.84  0.82
    4354     1.761  4.23  2.29  1.64  1.34  1.16  1.03  0.95  0.90  0.85  0.82
    4463     1.690  4.45  2.38  1.70  1.36  1.16  1.03  0.94  0.88  0.82  0.78
    4825     1.627  4.68  2.49  1.76  1.41  1.20  1.06  0.96  0.89  0.84  0.80
    5133     1.570  4.86  2.58  1.82  1.45  1.22  1.08  0.98  0.91  0.85  0.81
    5389     1.519  4.87  2.58  1.82  1.44  1.22  1.07  0.97  0.89  0.84  0.79
    4997     1.474  5.12  2.71  1.90  1.51  1.27  1.11  1.00  0.92  0.86  0.81
    3267     1.432  5.15  2.72  1.91  1.51  1.28  1.12  1.01  0.93  0.86  0.81
    1060     1.396  4.85  2.57  1.82  1.44  1.22  1.07  0.97  0.90  0.85  0.81
   65571   overall  3.44  1.98  1.50  1.27  1.13  1.04  0.98  0.93  0.90  0.88


 List of    500 reflections *NOT* obeying Wilson distribution (Z> 10.0)

   h    k    l     RES        Z       Intensity    Sigma

   40   20   82    1.49   82.09      0.1954E+02  0.6136E+01 "alien"
   32   30   87    1.47   77.18      0.1837E+02  0.6118E+01 "alien"
   64   20   17    1.47   76.58      0.1823E+02  0.5270E+01 "alien"
   55   43   18    1.48   76.51      0.1821E+02  0.5229E+01 "alien"
   29   71   29    1.46   69.63      0.1657E+02  0.4941E+01 "alien"
   15   43   88    1.49   69.33      0.1650E+02  0.6392E+01 "alien"
   40   16   83    1.49   69.06      0.1644E+02  0.6070E+01 "alien"
   30   28   92    1.45   68.84      0.1639E+02  0.5710E+01 "alien"
   52   20   65    1.46   66.24      0.1577E+02  0.5338E+01 "alien"
   39   25   81    1.49   66.12      0.1574E+02  0.5639E+01 "alien"
   49    5   77    1.45   65.47      0.2188E+02  0.6174E+01 "alien"
   26   38   87    1.47   65.41      0.1557E+02  0.5756E+01 "alien"
   46    4   79    1.47   65.25      0.1553E+02  0.5753E+01 "alien"
   13   47   87    1.47   65.06      0.1549E+02  0.6074E+01 "alien"
   26   38   86    1.48   62.36      0.1484E+02  0.5485E+01 "alien"
   60   32   26    1.46   61.06      0.1453E+02  0.5358E+01 "alien"
   31   31   86    1.49   60.87      0.1449E+02  0.6057E+01 "alien"
   52   50   19    1.46   60.78      0.1447E+02  0.5215E+01 "alien"
   14   42   91    1.47   60.47      0.1439E+02  0.5700E+01 "alien"
   23   33   93    1.47   59.12      0.1407E+02  0.5830E+01 "alien"
   55   23   57    1.45   58.69      0.1397E+02  0.5242E+01 "alien"
    7   45   90    1.48   58.30      0.1388E+02  0.5868E+01 "alien"
   29   33   86    1.49   58.10      0.1383E+02  0.5593E+01 "alien"
   15   47   84    1.49   58.02      0.1381E+02  0.5709E+01 "alien"
   38   16   86    1.49   57.78      0.1375E+02  0.5846E+01 "alien"
   51   39   48    1.47   57.66      0.1372E+02  0.5061E+01 "alien"
   61   31   14    1.48   57.48      0.1368E+02  0.5355E+01 "alien"
   21   39   89    1.48   56.94      0.1355E+02  0.6562E+01 "alien"
   17   43   87    1.49   56.13      0.1336E+02  0.5643E+01 "alien"
   42   14   81    1.49   55.36      0.1318E+02  0.5855E+01 "alien"
   36   30   82    1.48   54.73      0.1303E+02  0.5726E+01 "alien"
    4   44   91    1.48   54.58      0.1299E+02  0.5978E+01 "alien"
   62   28   14    1.47   54.35      0.1294E+02  0.5168E+01 "alien"
   38   32   77    1.49   54.25      0.1291E+02  0.5605E+01 "alien"
   63   25   20    1.46   54.05      0.1286E+02  0.5050E+01 "alien"
   23   39   88    1.48   54.03      0.1286E+02  0.6190E+01 "alien"
   24   72   30    1.48   53.32      0.1269E+02  0.4844E+01 "alien"
   29   67   36    1.49   52.97      0.1261E+02  0.4301E+01 "alien"
   20   46   85    1.46   52.84      0.1258E+02  0.6477E+01 "alien"
   36   24   86    1.48   52.75      0.1255E+02  0.5827E+01 "alien"
   10   48   88    1.46   52.44      0.1248E+02  0.6256E+01 "alien"
   54   44   22    1.48   52.17      0.1242E+02  0.5212E+01 "alien"
   15   43   90    1.47   52.09      0.1240E+02  0.6165E+01 "alien"
   53   23   59    1.47   51.98      0.1237E+02  0.4894E+01 "alien"
   13   39   94    1.47   51.76      0.1232E+02  0.5176E+01 "alien"
    2   78   28    1.48   51.64      0.1229E+02  0.4114E+01 "alien"
   59   37   22    1.45   51.64      0.1229E+02  0.5366E+01 "alien"
   46    4   77    1.49   51.33      0.1222E+02  0.5837E+01 "alien"
   53   25   56    1.48   51.16      0.1218E+02  0.5213E+01 "alien"
   54   44   28    1.46   51.09      0.1216E+02  0.5155E+01 "alien"
    9   43   90    1.49   51.08      0.1216E+02  0.5696E+01 "alien"
   54    4   62    1.49   50.59      0.1204E+02  0.5652E+01 "alien"
   52   48   19    1.48   50.28      0.1197E+02  0.4947E+01 "alien"
   29   39   84    1.47   50.08      0.1192E+02  0.6359E+01 "alien"
   66   10   18    1.46   50.08      0.1192E+02  0.4614E+01 "alien"
   15   47   85    1.48   49.95      0.1189E+02  0.5695E+01 "alien"
   24   34   90    1.49   49.87      0.1187E+02  0.5884E+01 "alien"
    4   48   87    1.48   49.85      0.1186E+02  0.5482E+01 "alien"
   19   45   83    1.50   49.84      0.2297E+02  0.6211E+01 "alien"
   55   21   52    1.49   49.74      0.1184E+02  0.4980E+01 "alien"
   56    6   57    1.49   49.56      0.1180E+02  0.5003E+01 "alien"
   33   23   89    1.48   49.43      0.1177E+02  0.6141E+01 "alien"
   30   28   90    1.48   49.34      0.1174E+02  0.5680E+01 "alien"
   17   37   93    1.48   49.06      0.1168E+02  0.6448E+01 "alien"
   32   34   83    1.49   48.73      0.1160E+02  0.5836E+01 "alien"
   36   34   80    1.47   48.60      0.1157E+02  0.5842E+01 "alien"
   15   41   90    1.49   48.54      0.1155E+02  0.6075E+01 "alien"
   56   42   26    1.45   48.37      0.1151E+02  0.5003E+01 "alien"
   42   58   32    1.48   47.87      0.1139E+02  0.4932E+01 "alien"
   50    4   76    1.44   47.77      0.1597E+02  0.6111E+01 "alien"
   54   46   27    1.45   47.77      0.1597E+02  0.5465E+01 "alien"
   48    8   76    1.47   47.58      0.1133E+02  0.5397E+01 "alien"
   51   17   66    1.48   47.54      0.1131E+02  0.4834E+01 "alien"
   39   61   34    1.47   47.53      0.1131E+02  0.4921E+01 "alien"
   56   22   54    1.46   47.52      0.1131E+02  0.5032E+01 "alien"
   54   44   18    1.49   47.31      0.1126E+02  0.4874E+01 "alien"
   32   70   20    1.47   47.18      0.1123E+02  0.4543E+01 "alien"
   42   22   78    1.49   47.17      0.1123E+02  0.5841E+01 "alien"
   54   44   19    1.49   47.00      0.1119E+02  0.5049E+01 "alien"
   45   55   31    1.48   46.92      0.1117E+02  0.4500E+01 "alien"
   30   38   84    1.47   46.66      0.1111E+02  0.5842E+01 "alien"
   36   20   87    1.49   46.31      0.1102E+02  0.5973E+01 "alien"
   27   43   82    1.47   46.23      0.1100E+02  0.5920E+01 "alien"
   25   31   92    1.48   45.88      0.1092E+02  0.5805E+01 "alien"
   65   23   18    1.43   45.80      0.1531E+02  0.5365E+01 "alien"
   25   71   29    1.49   45.67      0.1087E+02  0.4137E+01 "alien"
   28   28   90    1.49   45.49      0.1083E+02  0.5810E+01 "alien"
   40   62   30    1.46   44.75      0.1065E+02  0.4801E+01 "alien"
   64   14   17    1.49   44.65      0.1063E+02  0.4740E+01 "alien"
   23   33   91    1.49   44.48      0.1059E+02  0.5611E+01 "alien"
   54   48   11    1.46   44.23      0.1053E+02  0.5020E+01 "alien"
   37   31   81    1.47   44.19      0.1052E+02  0.5791E+01 "alien"
   18   76   26    1.47   44.17      0.1051E+02  0.4341E+01 "alien"
   38   62   29    1.49   44.14      0.1051E+02  0.4789E+01 "alien"
   21   37   91    1.47   44.06      0.1049E+02  0.5717E+01 "alien"
   53    7   71    1.43   44.05      0.1472E+02  0.5852E+01 "alien"
   33   33   83    1.48   43.90      0.1045E+02  0.5675E+01 "alien"
   39   61   37    1.46   43.87      0.1044E+02  0.4664E+01 "alien"
   33   69   25    1.46   43.66      0.1039E+02  0.4591E+01 "alien"
   17   79   25    1.43   43.62      0.1458E+02  0.4787E+01 "alien"
   18   74   29    1.49   43.62      0.1038E+02  0.4757E+01 "alien"
   41   63   23    1.46   43.49      0.1035E+02  0.4594E+01 "alien"
    4   46   90    1.47   43.40      0.1033E+02  0.5858E+01 "alien"
   45    9   79    1.48   43.19      0.1028E+02  0.5625E+01 "alien"
   48   12   73    1.49   42.78      0.1018E+02  0.5272E+01 "alien"
   19   45   87    1.46   42.77      0.1018E+02  0.5818E+01 "alien"
    6   50   85    1.48   42.74      0.1017E+02  0.5437E+01 "alien"
   54   46   17    1.47   42.56      0.1013E+02  0.5092E+01 "alien"
   53   43   33    1.47   42.47      0.1011E+02  0.4288E+01 "alien"
   57   15   52    1.48   42.46      0.1011E+02  0.4956E+01 "alien"
   61   35   12    1.45   42.46      0.1419E+02  0.5206E+01 "alien"
   62   34   15    1.43   42.38      0.1417E+02  0.5248E+01 "alien"
   61   29   20    1.48   42.29      0.1007E+02  0.4987E+01 "alien"
   33   23   88    1.49   41.98      0.9993E+01  0.5604E+01 "alien"
   50   48   36    1.46   41.92      0.9977E+01  0.4149E+01 "alien"
   25   39   86    1.48   41.91      0.9975E+01  0.6168E+01 "alien"
   11   41   92    1.48   41.76      0.9938E+01  0.5950E+01 "alien"
   53   13   71    1.42   41.73      0.1395E+02  0.5338E+01 "alien"
   65   15   18    1.47   41.63      0.9909E+01  0.4447E+01 "alien"
   33   35   82    1.48   41.52      0.9883E+01  0.5741E+01 "alien"
   18   74   35    1.47   41.44      0.9864E+01  0.4291E+01 "alien"
   28   70   27    1.49   41.44      0.9863E+01  0.4643E+01 "alien"
   64   24    1    1.47   41.31      0.9833E+01  0.3436E+01 "alien"
   28   32   88    1.49   41.28      0.9825E+01  0.5761E+01 "alien"
   42   22   79    1.48   40.90      0.9734E+01  0.5352E+01 "alien"
   28   36   86    1.48   40.87      0.9728E+01  0.5781E+01 "alien"
   32   26   88    1.49   40.78      0.9707E+01  0.5822E+01 "alien"
   54   22   60    1.45   40.77      0.9704E+01  0.5348E+01 "alien"
   31   29   88    1.48   40.76      0.9703E+01  0.5657E+01 "alien"
   66    6    7    1.48   40.65      0.9676E+01  0.2586E+01 "alien"
   54   18   60    1.47   40.61      0.9667E+01  0.5213E+01 "alien"
   62   28   17    1.47   40.59      0.9662E+01  0.4995E+01 "alien"
   21   77   20    1.45   40.57      0.9657E+01  0.4481E+01 "alien"
   26   74   30    1.43   40.57      0.1356E+02  0.4790E+01 "alien"
   56   44   16    1.46   40.57      0.9656E+01  0.4885E+01 "alien"
   46   56   30    1.45   40.56      0.9653E+01  0.4693E+01 "alien"
   33   29   87    1.47   40.45      0.9627E+01  0.5925E+01 "alien"
   64   32   10    1.42   40.37      0.1349E+02  0.5190E+01 "alien"
   24   44   82    1.49   40.34      0.9601E+01  0.6420E+01 "alien"
   55    7   63    1.46   40.32      0.9596E+01  0.5098E+01 "alien"
   67    1    6    1.47   40.17      0.9562E+01  0.3460E+01 "alien"
   13   51   81    1.49   40.14      0.9554E+01  0.5071E+01 "alien"
   39   31   79    1.47   40.13      0.9552E+01  0.4460E+01 "alien"
   65   13   11    1.48   40.12      0.9548E+01  0.4721E+01 "alien"
   65   21   13    1.45   40.11      0.9546E+01  0.4882E+01 "alien"
   62   26   18    1.48   39.95      0.9510E+01  0.5237E+01 "alien"
   47    1   78    1.47   39.92      0.9501E+01  0.3842E+01 "alien"
   31   29   90    1.46   39.62      0.9430E+01  0.5821E+01 "alien"
   47    9   76    1.48   39.55      0.9414E+01  0.5261E+01 "alien"
   23   41   87    1.47   39.53      0.9409E+01  0.6240E+01 "alien"
   54   48   18    1.45   39.51      0.1321E+02  0.5114E+01 "alien"
   64   28   13    1.44   39.43      0.1318E+02  0.5124E+01 "alien"
   53   37   46    1.46   39.24      0.9341E+01  0.4582E+01 "alien"
   18   48   82    1.49   39.20      0.9331E+01  0.5892E+01 "alien"
   52   12   68    1.46   39.17      0.9322E+01  0.5053E+01 "alien"
   44   58   32    1.45   39.16      0.9320E+01  0.4951E+01 "alien"
   60   40   11    1.43   39.10      0.1307E+02  0.5007E+01 "alien"
   32   24   89    1.49   39.09      0.9305E+01  0.5670E+01 "alien"
   29   25   91    1.49   38.91      0.9261E+01  0.5421E+01 "alien"
   55   15   66    1.42   38.85      0.1299E+02  0.4915E+01 "alien"
   33   31   87    1.46   38.83      0.9242E+01  0.5095E+01 "alien"
    7   53   80    1.50   38.75      0.9223E+01  0.5333E+01 "alien"
   35   67   37    1.42   38.70      0.1294E+02  0.4752E+01 "alien"
   12   48   85    1.48   38.65      0.9198E+01  0.5724E+01 "alien"
   27   71   30    1.47   38.65      0.9198E+01  0.4323E+01 "alien"
   54   42   31    1.47   38.63      0.9195E+01  0.4708E+01 "alien"
   63   21   21    1.48   38.62      0.9192E+01  0.4366E+01 "alien"
   51   51   14    1.48   38.54      0.9174E+01  0.4718E+01 "alien"
   55   29   47    1.48   38.50      0.9163E+01  0.4619E+01 "alien"
   28   32   89    1.48   38.42      0.9144E+01  0.5462E+01 "alien"
   19   77   12    1.48   38.41      0.9143E+01  0.2749E+01 "alien"
   55    1   60    1.49   38.40      0.9140E+01  0.5664E+01 "alien"
   59   37   12    1.47   38.34      0.9125E+01  0.5050E+01 "alien"
    5   53   83    1.47   38.27      0.9109E+01  0.5502E+01 "alien"
   45   55   33    1.47   38.19      0.9089E+01  0.4817E+01 "alien"
   12   78   25    1.47   38.17      0.9086E+01  0.4335E+01 "alien"
   61   35   21    1.43   37.83      0.1264E+02  0.5281E+01 "alien"
   50   14   68    1.49   37.80      0.8996E+01  0.5179E+01 "alien"
   63   23   15    1.48   37.74      0.8983E+01  0.4789E+01 "alien"
    3   79   27    1.47   37.67      0.8965E+01  0.4132E+01 "alien"
   65   19    6    1.47   37.65      0.8962E+01  0.4977E+01 "alien"
   65   19    7    1.47   37.61      0.8951E+01  0.5136E+01 "alien"
   32   32   86    1.47   37.59      0.8947E+01  0.5996E+01 "alien"
   46    2   77    1.50   37.56      0.8941E+01  0.3909E+01 "alien"
   33   23   90    1.47   37.54      0.8935E+01  0.6186E+01 "alien"
   34   68   33    1.44   37.52      0.1254E+02  0.4597E+01 "alien"
   28   72   37    1.42   37.49      0.1253E+02  0.4727E+01 "alien"
   59   41   19    1.43   37.28      0.1246E+02  0.5138E+01 "alien"
   56   16   55    1.48   37.26      0.8869E+01  0.5113E+01 "alien"
   29   69   32    1.48   37.26      0.8867E+01  0.4578E+01 "alien"
   60   34   22    1.46   37.19      0.8851E+01  0.5208E+01 "alien"
   17   37   95    1.45   37.16      0.8845E+01  0.6134E+01 "alien"
   31   67   34    1.48   37.16      0.8844E+01  0.4430E+01 "alien"
   18   44   86    1.49   37.14      0.8840E+01  0.5676E+01 "alien"
   26   40   86    1.46   37.03      0.8814E+01  0.5927E+01 "alien"
   29   69   33    1.47   37.00      0.8807E+01  0.4310E+01 "alien"
   56   16   54    1.48   36.93      0.8790E+01  0.4727E+01 "alien"
   36   62   38    1.48   36.88      0.8777E+01  0.4527E+01 "alien"
   56   30   45    1.47   36.77      0.8753E+01  0.4853E+01 "alien"
   39   27   80    1.48   36.76      0.8751E+01  0.6171E+01 "alien"
   35   63   38    1.48   36.64      0.8720E+01  0.4436E+01 "alien"
   52   38   48    1.46   36.63      0.8718E+01  0.4675E+01 "alien"
   36   28   82    1.49   36.59      0.8708E+01  0.5721E+01 "alien"
   40   24   81    1.48   36.54      0.8696E+01  0.5318E+01 "alien"
   54   32   44    1.49   36.52      0.8692E+01  0.4484E+01 "alien"
   53   39   37    1.49   36.49      0.8686E+01  0.4152E+01 "alien"
   44   54   34    1.49   36.40      0.8664E+01  0.4957E+01 "alien"
   28   40   86    1.45   36.38      0.1216E+02  0.5653E+01 "alien"
   66    2   11    1.48   36.35      0.8653E+01  0.3373E+01 "alien"
   10   78   27    1.47   36.33      0.8647E+01  0.4064E+01 "alien"
   60   32   10    1.49   36.33      0.8647E+01  0.5025E+01 "alien"
   60   30   23    1.48   36.32      0.8644E+01  0.5041E+01 "alien"
   51   55   19    1.42   36.27      0.1212E+02  0.4960E+01 "alien"
   36   64   38    1.45   36.24      0.1211E+02  0.4621E+01 "alien"
   52   12   64    1.50   36.20      0.8616E+01  0.5271E+01 "alien"
   57   15   56    1.45   36.17      0.8608E+01  0.4914E+01 "alien"
   17   77   22    1.47   36.16      0.8607E+01  0.4322E+01 "alien"
   44   18   77    1.49   36.03      0.8575E+01  0.5509E+01 "alien"
   27   69   37    1.47   36.01      0.8572E+01  0.4514E+01 "alien"
   19   73   36    1.48   36.00      0.8568E+01  0.4073E+01 "alien"
   54   18   67    1.42   35.99      0.1203E+02  0.5364E+01 "alien"
   49   55   20    1.45   35.68      0.1193E+02  0.5019E+01 "alien"
   53   19   62    1.47   35.68      0.8493E+01  0.5430E+01 "alien"
   33   23   81    1.58   35.66      0.1804E+02  0.6016E+01 "alien"
   57   25   53    1.43   35.66      0.1192E+02  0.5303E+01 "alien"
   25   71   31    1.48   35.65      0.8486E+01  0.4306E+01 "alien"
   43   19   79    1.48   35.64      0.8482E+01  0.5613E+01 "alien"
   51   51   13    1.48   35.64      0.8482E+01  0.4465E+01 "alien"
   56   34   42    1.45   35.63      0.8480E+01  0.4470E+01 "alien"
   54   36   45    1.46   35.59      0.8472E+01  0.4476E+01 "alien"
   45   59   33    1.42   35.50      0.1187E+02  0.4866E+01 "alien"
   53   17   62    1.48   35.44      0.8434E+01  0.4914E+01 "alien"
   28   34   89    1.46   35.37      0.8419E+01  0.5780E+01 "alien"
   54   10   63    1.47   35.35      0.8415E+01  0.4959E+01 "alien"
   29   41   83    1.46   35.35      0.8413E+01  0.5668E+01 "alien"
   37   23   84    1.49   35.31      0.8405E+01  0.5364E+01 "alien"
   39   65   22    1.46   35.14      0.8363E+01  0.4644E+01 "alien"
   48   58   27    1.41   35.14      0.1174E+02  0.4949E+01 "alien"
   61   35   20    1.43   35.12      0.1174E+02  0.4852E+01 "alien"
   65    7   16    1.49   35.08      0.8351E+01  0.4535E+01 "alien"
   59   35   23    1.46   34.97      0.8324E+01  0.5132E+01 "alien"
   50   54   15    1.46   34.84      0.8293E+01  0.5146E+01 "alien"
   44   10   79    1.50   34.84      0.8292E+01  0.5400E+01 "alien"
   12   44   82    1.56   34.80      0.1760E+02  0.6083E+01 "alien"
   63   19   19    1.49   34.80      0.8283E+01  0.4352E+01 "alien"
   54    4   63    1.48   34.79      0.8280E+01  0.5269E+01 "alien"
   56   18   53    1.48   34.78      0.8277E+01  0.4922E+01 "alien"
   54   38   42    1.46   34.76      0.8274E+01  0.4476E+01 "alien"
   63   23   16    1.48   34.74      0.8269E+01  0.5064E+01 "alien"
   30   26   92    1.47   34.67      0.8252E+01  0.5613E+01 "alien"
   11   77   31    1.47   34.63      0.8243E+01  0.4159E+01 "alien"
   55   43   24    1.47   34.62      0.8240E+01  0.5274E+01 "alien"
   36   68   34    1.41   34.54      0.1154E+02  0.4681E+01 "alien"
   62   28   10    1.48   34.53      0.8219E+01  0.4574E+01 "alien"
   19   75   23    1.49   34.44      0.8197E+01  0.4170E+01 "alien"
   40   10   80    1.55   34.36      0.1738E+02  0.6086E+01 "alien"
   41    9   85    1.48   34.35      0.8177E+01  0.5752E+01 "alien"
   45   55   35    1.46   34.35      0.8176E+01  0.4853E+01 "alien"
   10   80   25    1.44   34.33      0.1148E+02  0.4245E+01 "alien"
   59   31   24    1.49   34.32      0.8169E+01  0.4753E+01 "alien"
   52   24   59    1.48   34.30      0.8164E+01  0.5286E+01 "alien"
   44   58   30    1.46   34.27      0.8157E+01  0.4462E+01 "alien"
   43   59   30    1.46   34.26      0.8154E+01  0.4962E+01 "alien"
   50   46   36    1.48   34.22      0.8145E+01  0.4015E+01 "alien"
   54   46   12    1.48   34.21      0.8143E+01  0.4826E+01 "alien"
   27   69   36    1.48   34.21      0.8142E+01  0.4581E+01 "alien"
   16   44   85    1.51   34.16      0.1575E+02  0.6118E+01 "alien"
   54   36   38    1.49   34.11      0.8118E+01  0.4413E+01 "alien"
   45    3   81    1.47   34.05      0.8105E+01  0.5750E+01 "alien"
   26   42   83    1.48   34.01      0.8094E+01  0.5679E+01 "alien"
   23   79   28    1.39   33.97      0.1670E+02  0.4810E+01 "alien"
   18   36   90    1.52   33.91      0.1563E+02  0.6100E+01 "alien"
   17   75   27    1.49   33.80      0.8044E+01  0.4540E+01 "alien"
   21   35   87    1.54   33.76      0.1556E+02  0.6562E+01 "alien"
   59   41   13    1.44   33.73      0.1127E+02  0.4849E+01 "alien"
   31   27   89    1.48   33.71      0.8024E+01  0.6117E+01 "alien"
   22   42   87    1.47   33.65      0.8009E+01  0.6308E+01 "alien"
   39   61   30    1.49   33.51      0.7977E+01  0.4725E+01 "alien"
   46   20   73    1.49   33.45      0.7962E+01  0.5370E+01 "alien"
   34   68   37    1.42   33.38      0.1116E+02  0.4543E+01 "alien"
   51   41   23    1.57   33.33      0.1686E+02  0.5280E+01 "alien"
   31   27   90    1.47   33.30      0.7925E+01  0.5675E+01 "alien"
   50   44   40    1.48   33.28      0.7922E+01  0.4381E+01 "alien"
   65   13   27    1.45   33.28      0.1112E+02  0.4858E+01 "alien"
   53   29   56    1.46   33.27      0.7919E+01  0.4723E+01 "alien"
   52   44   29    1.50   33.25      0.7913E+01  0.4805E+01 "alien"
   22   40   88    1.47   33.24      0.7913E+01  0.5930E+01 "alien"
   56   42   21    1.47   33.24      0.7913E+01  0.5078E+01 "alien"
   54    6   63    1.48   33.24      0.7912E+01  0.4897E+01 "alien"
   14   82   13    1.42   33.23      0.1111E+02  0.3275E+01 "alien"
   36   16   88    1.49   33.22      0.7907E+01  0.5752E+01 "alien"
   16   76   33    1.46   33.22      0.7906E+01  0.4145E+01 "alien"
   34   66   37    1.45   33.20      0.1110E+02  0.4536E+01 "alien"
   46   14   74    1.50   33.20      0.1530E+02  0.5581E+01 "alien"
   37   67   19    1.46   33.19      0.7900E+01  0.4686E+01 "alien"
   33   69   34    1.43   33.15      0.1108E+02  0.4415E+01 "alien"
    6   48   86    1.49   33.12      0.7882E+01  0.5450E+01 "alien"
   62   36   12    1.42   33.07      0.1105E+02  0.5042E+01 "alien"
   50   52   34    1.43   33.04      0.1104E+02  0.4845E+01 "alien"
   24   36   85    1.53   33.03      0.1522E+02  0.6242E+01 "alien"
   51   47   27    1.49   33.01      0.7857E+01  0.3070E+01 "alien"
   46   10   77    1.48   32.98      0.7849E+01  0.5561E+01 "alien"
   65   11   15    1.48   32.97      0.7848E+01  0.4544E+01 "alien"
   55   31   45    1.48   32.94      0.7841E+01  0.4331E+01 "alien"
    8   44   92    1.46   32.93      0.7838E+01  0.5902E+01 "alien"
   35   25   86    1.48   32.88      0.7826E+01  0.5854E+01 "alien"
   23   77   24    1.43   32.85      0.1098E+02  0.4789E+01 "alien"
   47    1   79    1.46   32.83      0.7814E+01  0.3865E+01 "alien"
   68    6   14    1.43   32.83      0.1097E+02  0.5244E+01 "alien"
   16   76   24    1.49   32.80      0.7807E+01  0.4341E+01 "alien"
   55   43   31    1.44   32.77      0.1095E+02  0.4921E+01 "alien"
   55   23   51    1.49   32.77      0.7799E+01  0.4587E+01 "alien"
   20   36   87    1.54   32.76      0.1510E+02  0.6125E+01 "alien"
   17   47   83    1.49   32.73      0.7791E+01  0.6176E+01 "alien"
   65   25    6    1.44   32.70      0.1093E+02  0.4980E+01 "alien"
   20   74   30    1.48   32.69      0.7781E+01  0.4255E+01 "alien"
    6   50   84    1.49   32.68      0.7779E+01  0.5301E+01 "alien"
   57   37   21    1.49   32.66      0.7773E+01  0.4719E+01 "alien"
   22   36   91    1.48   32.65      0.7770E+01  0.6241E+01 "alien"
   66   12    4    1.47   32.64      0.7770E+01  0.3363E+01 "alien"
   61   25   29    1.47   32.61      0.7761E+01  0.4324E+01 "alien"
   47    1   76    1.49   32.57      0.7752E+01  0.3747E+01 "alien"
   65    3   17    1.49   32.54      0.7745E+01  0.4695E+01 "alien"
   53   13   66    1.46   32.46      0.7725E+01  0.4879E+01 "alien"
   22   34   93    1.47   32.42      0.7716E+01  0.6118E+01 "alien"
   34   66   26    1.49   32.41      0.7713E+01  0.4340E+01 "alien"
   62   32    7    1.46   32.40      0.7711E+01  0.4757E+01 "alien"
   66    8   12    1.47   32.39      0.7710E+01  0.4615E+01 "alien"
   67   21    3    1.42   32.39      0.1083E+02  0.4927E+01 "alien"
   54   50   21    1.42   32.31      0.1080E+02  0.4936E+01 "alien"
   51   13   59    1.55   32.30      0.1634E+02  0.5393E+01 "alien"
   37   63   28    1.49   32.25      0.7676E+01  0.4521E+01 "alien"
   39   61   38    1.45   32.20      0.7663E+01  0.4946E+01 "alien"
   50   54   31    1.42   32.20      0.1076E+02  0.4789E+01 "alien"
   15   47   86    1.47   32.14      0.7649E+01  0.5816E+01 "alien"
   54    6   70    1.42   32.11      0.1073E+02  0.5722E+01 "alien"
    9   43   89    1.50   32.11      0.1480E+02  0.6290E+01 "alien"
   44   18   75    1.51   32.06      0.1478E+02  0.5612E+01 "alien"
   67    1   11    1.46   31.99      0.7615E+01  0.3444E+01 "alien"
   68    6   11    1.44   31.98      0.1069E+02  0.3571E+01 "alien"
   66   20   11    1.44   31.95      0.1068E+02  0.4850E+01 "alien"
   60   30   25    1.48   31.87      0.7584E+01  0.4610E+01 "alien"
   51   41   46    1.46   31.86      0.7584E+01  0.4410E+01 "alien"
   18   40   88    1.50   31.85      0.1468E+02  0.6430E+01 "alien"
   18   38   91    1.49   31.79      0.7568E+01  0.5706E+01 "alien"
   21   77   19    1.45   31.79      0.7566E+01  0.4287E+01 "alien"
   42   16   68    1.63   31.72      0.1850E+02  0.5596E+01 "alien"
   60   38   12    1.45   31.70      0.1059E+02  0.5181E+01 "alien"
    5   51   84    1.48   31.66      0.7534E+01  0.3861E+01 "alien"
   15   77   31    1.45   31.65      0.7533E+01  0.4269E+01 "alien"
   52   28   58    1.47   31.55      0.7509E+01  0.4809E+01 "alien"
   55   47   27    1.42   31.50      0.1053E+02  0.4241E+01 "alien"
   11   43   90    1.49   31.42      0.7478E+01  0.5890E+01 "alien"
   55   27   47    1.49   31.41      0.7477E+01  0.4434E+01 "alien"
   55   17   65    1.42   31.41      0.1050E+02  0.5159E+01 "alien"
   56   30   53    1.42   31.38      0.1049E+02  0.4917E+01 "alien"
    6   80   15    1.48   31.36      0.7465E+01  0.3713E+01 "alien"
   38   30   81    1.47   31.35      0.7463E+01  0.4646E+01 "alien"
   61   31   22    1.46   31.35      0.7461E+01  0.4892E+01 "alien"
   31   73   28    1.41   31.33      0.1047E+02  0.4591E+01 "alien"
   43   13   80    1.49   31.27      0.7444E+01  0.5989E+01 "alien"
   53   39   24    1.54   31.27      0.1582E+02  0.5131E+01 "alien"
   59   35   12    1.49   31.21      0.7429E+01  0.4817E+01 "alien"
   39   17   78    1.56   31.11      0.1573E+02  0.5675E+01 "alien"
   53   39   44    1.46   31.07      0.7395E+01  0.4412E+01 "alien"
   34   24   89    1.47   31.03      0.7387E+01  0.4574E+01 "alien"
   59   39   19    1.44   30.97      0.1035E+02  0.5064E+01 "alien"
   58   32   19    1.52   30.96      0.1427E+02  0.4973E+01 "alien"
   53   21   58    1.49   30.95      0.7367E+01  0.5053E+01 "alien"
   53   33   47    1.49   30.94      0.7364E+01  0.4403E+01 "alien"
   19   37   92    1.48   30.93      0.7362E+01  0.6390E+01 "alien"
   61   31    6    1.48   30.93      0.7361E+01  0.4821E+01 "alien"
    1   53   83    1.47   30.88      0.7349E+01  0.3906E+01 "alien"
   54   48   19    1.45   30.86      0.1032E+02  0.4848E+01 "alien"
   36   68   33    1.42   30.86      0.1032E+02  0.4739E+01 "alien"
   52   12   70    1.45   30.81      0.1030E+02  0.4951E+01 "alien"
   53   29   23    1.64   30.81      0.1797E+02  0.5322E+01 "alien"
   63   25   13    1.47   30.79      0.7329E+01  0.4890E+01 "alien"
   26   74   32    1.43   30.77      0.1029E+02  0.4475E+01 "alien"
   35   21   86    1.50   30.75      0.1417E+02  0.5662E+01 "alien"
   56   18   55    1.47   30.73      0.7315E+01  0.5196E+01 "alien"
   33   67   25    1.49   30.70      0.7308E+01  0.4313E+01 "alien"
   42   14   77    1.54   30.69      0.1414E+02  0.5803E+01 "alien"
   25   35   88    1.49   30.65      0.7295E+01  0.5499E+01 "alien"
    5   79   26    1.47   30.61      0.7285E+01  0.3881E+01 "alien"
    6   78   27    1.48   30.59      0.7280E+01  0.3888E+01 "alien"
   25   71   35    1.47   30.55      0.7272E+01  0.4231E+01 "alien"
   55   37   41    1.45   30.55      0.7271E+01  0.4317E+01 "alien"
   55   13   59    1.48   30.55      0.7271E+01  0.5101E+01 "alien"
   60   30   14    1.50   30.49      0.1405E+02  0.4961E+01 "alien"
   53   27   59    1.45   30.48      0.1019E+02  0.5130E+01 "alien"
   42    8   78    1.54   30.43      0.1402E+02  0.5795E+01 "alien"
   54   28   25    1.62   30.42      0.1775E+02  0.5202E+01 "alien"
   66    4   17    1.47   30.42      0.7241E+01  0.4608E+01 "alien"
   42   58   37    1.46   30.39      0.7234E+01  0.5082E+01 "alien"
   43   55   36    1.49   30.37      0.7228E+01  0.4534E+01 "alien"
   22   38   88    1.49   30.34      0.7222E+01  0.6133E+01 "alien"
   66   18    2    1.45   30.34      0.7220E+01  0.4843E+01 "alien"
   53    5   71    1.43   30.33      0.1014E+02  0.5454E+01 "alien"
   62   22   28    1.47   30.33      0.7218E+01  0.4131E+01 "alien"
   62   20   32    1.47   30.31      0.7215E+01  0.4630E+01 "alien"
   29   37   85    1.47   30.31      0.7214E+01  0.5495E+01 "alien"
   20   74   33    1.47   30.26      0.7202E+01  0.4219E+01 "alien"
   28   38   85    1.47   30.24      0.7198E+01  0.5599E+01 "alien"
   36   64   34    1.47   30.21      0.7192E+01  0.4368E+01 "alien"
   46   56   25    1.47   30.18      0.7182E+01  0.2937E+01 "alien"
   40   66   21    1.43   30.08      0.1005E+02  0.4996E+01 "alien"
   55   43   23    1.47   30.06      0.7154E+01  0.4518E+01 "alien"
    6   54   80    1.48   30.05      0.7153E+01  0.5271E+01 "alien"
   37   13   78    1.61   30.03      0.1751E+02  0.5685E+01 "alien"
   55   19   55    1.48   29.99      0.7137E+01  0.4861E+01 "alien"
   29   73   23    1.44   29.98      0.1002E+02  0.4497E+01 "alien"
   39   13   86    1.48   29.97      0.7134E+01  0.6035E+01 "alien"
   34   24   79    1.58   29.94      0.1514E+02  0.6153E+01 "alien"
   68    4   11    1.44   29.93      0.1000E+02  0.4616E+01 "alien"
   44   56   31    1.48   29.85      0.7104E+01  0.4817E+01 "alien"
   32   34   85    1.47   29.80      0.7094E+01  0.5433E+01 "alien"
   54    6   66    1.46   29.80      0.7094E+01  0.5039E+01 "alien"
    3   45   91    1.47   29.80      0.7093E+01  0.5993E+01 "alien"
   12   76   33    1.47   29.76      0.7083E+01  0.3912E+01 "alien"
    8   48   87    1.48   29.74      0.7080E+01  0.5832E+01 "alien"
   41   63   32    1.43   29.72      0.9933E+01  0.4714E+01 "alien"
   22   32   94    1.47   29.71      0.7071E+01  0.5641E+01 "alien"
   56    8   63    1.44   29.70      0.9926E+01  0.5043E+01 "alien"
    5   79   29    1.46   29.69      0.7067E+01  0.3920E+01 "alien"
   60   38   21    1.43   29.64      0.9906E+01  0.5273E+01 "alien"
   53   39   43    1.46   29.62      0.7051E+01  0.4306E+01 "alien"
   53   23   63    1.44   29.61      0.9896E+01  0.4753E+01 "alien"
   22   36   92    1.46   29.56      0.7037E+01  0.6033E+01 "alien"
   10   40   89    1.53   29.56      0.1362E+02  0.5157E+01 "alien"
   25   75   33    1.42   29.55      0.9876E+01  0.4713E+01 "alien"
   52    6   72    1.44   29.50      0.9859E+01  0.5507E+01 "alien"
   56   38   29    1.48   29.47      0.7014E+01  0.4735E+01 "alien"
   52    6   67    1.48   29.47      0.7014E+01  0.3879E+01 "alien"
   34   70   27    1.43   29.46      0.9845E+01  0.4488E+01 "alien"
   16   38   95    1.45   29.44      0.7008E+01  0.6020E+01 "alien"
   10   50   85    1.47   29.41      0.7000E+01  0.5327E+01 "alien"
   41   63   21    1.46   29.38      0.6994E+01  0.4646E+01 "alien"
   61   35   25    1.42   29.36      0.9813E+01  0.5307E+01 "alien"
   46   54   31    1.48   29.35      0.6986E+01  0.4567E+01 "alien"
   57   39   25    1.46   29.35      0.6986E+01  0.5109E+01 "alien"
   18   44   80    1.55   29.34      0.1484E+02  0.6097E+01 "alien"
   53   35   24    1.58   29.31      0.1483E+02  0.5025E+01 "alien"
   54    6   65    1.46   29.31      0.6976E+01  0.4827E+01 "alien"
   59   37   16    1.47   29.31      0.6976E+01  0.4725E+01 "alien"
   59   35   13    1.49   29.30      0.6974E+01  0.4814E+01 "alien"
   35   29   81    1.51   29.29      0.1350E+02  0.5872E+01 "alien"
   49   53   17    1.48   29.28      0.6968E+01  0.4688E+01 "alien"
   54   16   66    1.43   29.27      0.9782E+01  0.5175E+01 "alien"
   41   61   30    1.46   29.27      0.6966E+01  0.4658E+01 "alien"
   52   50   12    1.47   29.26      0.6965E+01  0.5200E+01 "alien"
   38   30   80    1.48   29.24      0.6960E+01  0.6108E+01 "alien"
   64   12   19    1.49   29.23      0.6957E+01  0.4215E+01 "alien"
   45   57   28    1.46   29.22      0.6955E+01  0.4939E+01 "alien"
   34   66   34    1.46   29.17      0.6944E+01  0.4337E+01 "alien"
   53   21   55    1.51   29.17      0.1344E+02  0.5244E+01 "alien"
   51    5   71    1.47   29.14      0.6935E+01  0.3821E+01 "alien"
   53   45   40    1.42   29.13      0.9735E+01  0.4331E+01 "alien"
   21   35   92    1.48   29.10      0.6927E+01  0.5865E+01 "alien"
   53   31   52    1.47   29.09      0.6924E+01  0.4457E+01 "alien"
   29   37   86    1.46   29.07      0.6920E+01  0.5687E+01 "alien"
   37   65   37    1.43   29.06      0.9712E+01  0.5001E+01 "alien"
   52   34   47    1.50   29.05      0.1339E+02  0.4916E+01 "alien"
   22   36   77    1.65   29.04      0.1694E+02  0.6421E+01 "alien"
   36   62   31    1.51   29.01      0.1337E+02  0.4952E+01 "alien"
   15   77   20    1.49   28.97      0.6896E+01  0.3946E+01 "alien"
   60   22   35    1.49   28.97      0.6894E+01  0.4147E+01 "alien"
   68    4   10    1.44   28.94      0.9674E+01  0.5030E+01 "alien"
   62   32   24    1.43   28.94      0.9672E+01  0.4589E+01 "alien"
   43    7   83    1.47   28.93      0.6887E+01  0.5443E+01 "alien"
   44   16   78    1.49   28.93      0.6886E+01  0.5404E+01 "alien"
   14   40   94    1.46   28.88      0.6873E+01  0.5570E+01 "alien"
   64   24    8    1.46   28.87      0.6871E+01  0.4877E+01 "alien"
   66    8   19    1.46   28.83      0.6861E+01  0.4592E+01 "alien"
   35   71   24    1.41   28.82      0.9634E+01  0.4601E+01 "alien"
   51   53   20    1.44   28.81      0.9630E+01  0.4942E+01 "alien"
   68   16    1    1.42   28.81      0.9630E+01  0.3468E+01 "alien"
   55   25   56    1.45   28.81      0.9629E+01  0.4881E+01 "alien"
   66    4   16    1.47   28.81      0.6857E+01  0.4590E+01 "alien"
   39   21   83    1.49   28.81      0.6856E+01  0.5645E+01 "alien"
   52   24   60    1.48   28.79      0.6853E+01  0.4899E+01 "alien"
   41    9   84    1.49   28.79      0.6853E+01  0.5608E+01 "alien"
   65   29   13    1.41   28.77      0.9616E+01  0.4816E+01 "alien"
   40   62   20    1.49   28.77      0.6847E+01  0.4651E+01 "alien"
   65   19   12    1.46   28.76      0.6846E+01  0.4849E+01 "alien"
   65    9   11    1.49   28.75      0.6842E+01  0.4506E+01 "alien"
   56   10   58    1.47   28.74      0.6842E+01  0.4515E+01 "alien"
   59   41    8    1.44   28.69      0.9590E+01  0.4759E+01 "alien"
   44    4   76    1.54   28.69      0.1322E+02  0.5602E+01 "alien"
   35   35   81    1.47   28.68      0.6826E+01  0.5653E+01 "alien"
   34   64   26    1.52   28.61      0.1318E+02  0.5088E+01 "alien"
   57   13   56    1.46   28.55      0.6796E+01  0.4914E+01 "alien"
    7   79   17    1.49   28.51      0.6787E+01  0.3598E+01 "alien"
   22   42   85    1.49   28.51      0.6787E+01  0.5975E+01 "alien"
   26   30   92    1.48   28.47      0.6777E+01  0.5641E+01 "alien"
   32   30   88    1.46   28.42      0.6765E+01  0.5762E+01 "alien"
   52    4   71    1.45   28.42      0.6765E+01  0.3937E+01 "alien"
   48    6   74    1.49   28.39      0.6758E+01  0.3812E+01 "alien"
   12   46   87    1.48   28.37      0.6752E+01  0.5881E+01 "alien"
   61   31   10    1.48   28.35      0.6749E+01  0.4770E+01 "alien"


 List of    500 reflections *NOT* obeying Wilson distribution (sorted by resolution)
 Ice rings could occur at (Angstrom):
 3.897,3.669,3.441, 2.671,2.249,2.072, 1.948,1.918,1.883,1.721

   h    k    l     RES        Z       Intensity    Sigma

   23   79   28    1.39   33.97      0.1670E+02  0.4810E+01
   65   29   13    1.41   28.77      0.9616E+01  0.4816E+01
   31   73   28    1.41   31.33      0.1047E+02  0.4591E+01
   36   68   34    1.41   34.54      0.1154E+02  0.4681E+01
   48   58   27    1.41   35.14      0.1174E+02  0.4949E+01
   35   71   24    1.41   28.82      0.9634E+01  0.4601E+01
   25   75   33    1.42   29.55      0.9876E+01  0.4713E+01
   50   54   31    1.42   32.20      0.1076E+02  0.4789E+01
   64   32   10    1.42   40.37      0.1349E+02  0.5190E+01
   36   68   33    1.42   30.86      0.1032E+02  0.4739E+01
   54   18   67    1.42   35.99      0.1203E+02  0.5364E+01
   53   13   71    1.42   41.73      0.1395E+02  0.5338E+01
   68   16    1    1.42   28.81      0.9630E+01  0.3468E+01
   14   82   13    1.42   33.23      0.1111E+02  0.3275E+01
   55   15   66    1.42   38.85      0.1299E+02  0.4915E+01
   28   72   37    1.42   37.49      0.1253E+02  0.4727E+01
   55   17   65    1.42   31.41      0.1050E+02  0.5159E+01
   67   21    3    1.42   32.39      0.1083E+02  0.4927E+01
   56   30   53    1.42   31.38      0.1049E+02  0.4917E+01
   55   47   27    1.42   31.50      0.1053E+02  0.4241E+01
   34   68   37    1.42   33.38      0.1116E+02  0.4543E+01
   61   35   25    1.42   29.36      0.9813E+01  0.5307E+01
   45   59   33    1.42   35.50      0.1187E+02  0.4866E+01
   51   55   19    1.42   36.27      0.1212E+02  0.4960E+01
   62   36   12    1.42   33.07      0.1105E+02  0.5042E+01
   53   45   40    1.42   29.13      0.9735E+01  0.4331E+01
   54   50   21    1.42   32.31      0.1080E+02  0.4936E+01
   35   67   37    1.42   38.70      0.1294E+02  0.4752E+01
   54    6   70    1.42   32.11      0.1073E+02  0.5722E+01
   50   52   34    1.43   33.04      0.1104E+02  0.4845E+01
   26   74   32    1.43   30.77      0.1029E+02  0.4475E+01
   59   41   19    1.43   37.28      0.1246E+02  0.5138E+01
   62   32   24    1.43   28.94      0.9672E+01  0.4589E+01
   23   77   24    1.43   32.85      0.1098E+02  0.4789E+01
   41   63   32    1.43   29.72      0.9933E+01  0.4714E+01
   60   38   21    1.43   29.64      0.9906E+01  0.5273E+01
   34   70   27    1.43   29.46      0.9845E+01  0.4488E+01
   17   79   25    1.43   43.62      0.1458E+02  0.4787E+01
   33   69   34    1.43   33.15      0.1108E+02  0.4415E+01
   37   65   37    1.43   29.06      0.9712E+01  0.5001E+01
   60   40   11    1.43   39.10      0.1307E+02  0.5007E+01
   68    6   14    1.43   32.83      0.1097E+02  0.5244E+01
   53    7   71    1.43   44.05      0.1472E+02  0.5852E+01
   57   25   53    1.43   35.66      0.1192E+02  0.5303E+01
   61   35   21    1.43   37.83      0.1264E+02  0.5281E+01
   54   16   66    1.43   29.27      0.9782E+01  0.5175E+01
   62   34   15    1.43   42.38      0.1417E+02  0.5248E+01
   26   74   30    1.43   40.57      0.1356E+02  0.4790E+01
   40   66   21    1.43   30.08      0.1005E+02  0.4996E+01
   65   23   18    1.43   45.80      0.1531E+02  0.5365E+01
   53    5   71    1.43   30.33      0.1014E+02  0.5454E+01
   61   35   20    1.43   35.12      0.1174E+02  0.4852E+01
   68    6   11    1.44   31.98      0.1069E+02  0.3571E+01
   64   28   13    1.44   39.43      0.1318E+02  0.5124E+01
   34   68   33    1.44   37.52      0.1254E+02  0.4597E+01
   68    4   11    1.44   29.93      0.1000E+02  0.4616E+01
   59   41   13    1.44   33.73      0.1127E+02  0.4849E+01
   68    4   10    1.44   28.94      0.9674E+01  0.5030E+01
   66   20   11    1.44   31.95      0.1068E+02  0.4850E+01
   65   25    6    1.44   32.70      0.1093E+02  0.4980E+01
   50    4   76    1.44   47.77      0.1597E+02  0.6111E+01
   52    6   72    1.44   29.50      0.9859E+01  0.5507E+01
   56    8   63    1.44   29.70      0.9926E+01  0.5043E+01
   10   80   25    1.44   34.33      0.1148E+02  0.4245E+01
   51   53   20    1.44   28.81      0.9630E+01  0.4942E+01
   59   39   19    1.44   30.97      0.1035E+02  0.5064E+01
   53   23   63    1.44   29.61      0.9896E+01  0.4753E+01
   59   41    8    1.44   28.69      0.9590E+01  0.4759E+01
   29   73   23    1.44   29.98      0.1002E+02  0.4497E+01
   55   43   31    1.44   32.77      0.1095E+02  0.4921E+01
   60   38   12    1.45   31.70      0.1059E+02  0.5181E+01
   52   12   70    1.45   30.81      0.1030E+02  0.4951E+01
   49    5   77    1.45   65.47      0.2188E+02  0.6174E+01
   54   46   27    1.45   47.77      0.1597E+02  0.5465E+01
   28   40   86    1.45   36.38      0.1216E+02  0.5653E+01
   55   25   56    1.45   28.81      0.9629E+01  0.4881E+01
   65   13   27    1.45   33.28      0.1112E+02  0.4858E+01
   54   48   19    1.45   30.86      0.1032E+02  0.4848E+01
   34   66   37    1.45   33.20      0.1110E+02  0.4536E+01
   61   35   12    1.45   42.46      0.1419E+02  0.5206E+01
   36   64   38    1.45   36.24      0.1211E+02  0.4621E+01
   53   27   59    1.45   30.48      0.1019E+02  0.5130E+01
   54   48   18    1.45   39.51      0.1321E+02  0.5114E+01
   49   55   20    1.45   35.68      0.1193E+02  0.5019E+01
   21   77   20    1.45   40.57      0.9657E+01  0.4481E+01
   55   23   57    1.45   58.69      0.1397E+02  0.5242E+01
   52    4   71    1.45   28.42      0.6765E+01  0.3937E+01
   44   58   32    1.45   39.16      0.9320E+01  0.4951E+01
   16   38   95    1.45   29.44      0.7008E+01  0.6020E+01
   65   21   13    1.45   40.11      0.9546E+01  0.4882E+01
   59   37   22    1.45   51.64      0.1229E+02  0.5366E+01
   15   77   31    1.45   31.65      0.7533E+01  0.4269E+01
   54   22   60    1.45   40.77      0.9704E+01  0.5348E+01
   56   42   26    1.45   48.37      0.1151E+02  0.5003E+01
   21   77   19    1.45   31.79      0.7566E+01  0.4287E+01
   66   18    2    1.45   30.34      0.7220E+01  0.4843E+01
   30   28   92    1.45   68.84      0.1639E+02  0.5710E+01
   55   37   41    1.45   30.55      0.7271E+01  0.4317E+01
   56   34   42    1.45   35.63      0.8480E+01  0.4470E+01
   39   61   38    1.45   32.20      0.7663E+01  0.4946E+01
   17   37   95    1.45   37.16      0.8845E+01  0.6134E+01
   46   56   30    1.45   40.56      0.9653E+01  0.4693E+01
   57   15   56    1.45   36.17      0.8608E+01  0.4914E+01
   14   40   94    1.46   28.88      0.6873E+01  0.5570E+01
   60   34   22    1.46   37.19      0.8851E+01  0.5208E+01
   54    6   66    1.46   29.80      0.7094E+01  0.5039E+01
   16   76   33    1.46   33.22      0.7906E+01  0.4145E+01
   41   63   23    1.46   43.49      0.1035E+02  0.4594E+01
   29   71   29    1.46   69.63      0.1657E+02  0.4941E+01
   53   39   44    1.46   31.07      0.7395E+01  0.4412E+01
   62   32    7    1.46   32.40      0.7711E+01  0.4757E+01
   39   65   22    1.46   35.14      0.8363E+01  0.4644E+01
   50   54   15    1.46   34.84      0.8293E+01  0.5146E+01
   33   31   87    1.46   38.83      0.9242E+01  0.5095E+01
    5   79   29    1.46   29.69      0.7067E+01  0.3920E+01
   61   31   22    1.46   31.35      0.7461E+01  0.4892E+01
   56   22   54    1.46   47.52      0.1131E+02  0.5032E+01
   54   38   42    1.46   34.76      0.8274E+01  0.4476E+01
   52   20   65    1.46   66.24      0.1577E+02  0.5338E+01
   66   10   18    1.46   50.08      0.1192E+02  0.4614E+01
   54   36   45    1.46   35.59      0.8472E+01  0.4476E+01
   42   58   37    1.46   30.39      0.7234E+01  0.5082E+01
   53   13   66    1.46   32.46      0.7725E+01  0.4879E+01
   53   29   56    1.46   33.27      0.7919E+01  0.4723E+01
   60   32   26    1.46   61.06      0.1453E+02  0.5358E+01
   19   45   87    1.46   42.77      0.1018E+02  0.5818E+01
   39   61   37    1.46   43.87      0.1044E+02  0.4664E+01
   44   58   30    1.46   34.27      0.8157E+01  0.4462E+01
   31   29   90    1.46   39.62      0.9430E+01  0.5821E+01
   63   25   20    1.46   54.05      0.1286E+02  0.5050E+01
   56   44   16    1.46   40.57      0.9656E+01  0.4885E+01
   50   48   36    1.46   41.92      0.9977E+01  0.4149E+01
   29   41   83    1.46   35.35      0.8413E+01  0.5668E+01
   52   38   48    1.46   36.63      0.8718E+01  0.4675E+01
   67    1   11    1.46   31.99      0.7615E+01  0.3444E+01
   33   69   25    1.46   43.66      0.1039E+02  0.4591E+01
   10   48   88    1.46   52.44      0.1248E+02  0.6256E+01
   55    7   63    1.46   40.32      0.9596E+01  0.5098E+01
   66    8   19    1.46   28.83      0.6861E+01  0.4592E+01
   43   59   30    1.46   34.26      0.8154E+01  0.4962E+01
   37   67   19    1.46   33.19      0.7900E+01  0.4686E+01
   47    1   79    1.46   32.83      0.7814E+01  0.3865E+01
   57   13   56    1.46   28.55      0.6796E+01  0.4914E+01
   40   62   30    1.46   44.75      0.1065E+02  0.4801E+01
   41   61   30    1.46   29.27      0.6966E+01  0.4658E+01
   34   66   34    1.46   29.17      0.6944E+01  0.4337E+01
   52   50   19    1.46   60.78      0.1447E+02  0.5215E+01
   41   63   21    1.46   29.38      0.6994E+01  0.4646E+01
   53   39   43    1.46   29.62      0.7051E+01  0.4306E+01
   51   41   46    1.46   31.86      0.7584E+01  0.4410E+01
   65   19   12    1.46   28.76      0.6846E+01  0.4849E+01
   45   55   35    1.46   34.35      0.8176E+01  0.4853E+01
   52   12   68    1.46   39.17      0.9322E+01  0.5053E+01
   53   37   46    1.46   39.24      0.9341E+01  0.4582E+01
    8   44   92    1.46   32.93      0.7838E+01  0.5902E+01
   54   48   11    1.46   44.23      0.1053E+02  0.5020E+01
   29   37   86    1.46   29.07      0.6920E+01  0.5687E+01
   20   46   85    1.46   52.84      0.1258E+02  0.6477E+01
   54   44   28    1.46   51.09      0.1216E+02  0.5155E+01
   54    6   65    1.46   29.31      0.6976E+01  0.4827E+01
   32   30   88    1.46   28.42      0.6765E+01  0.5762E+01
   45   57   28    1.46   29.22      0.6955E+01  0.4939E+01
   28   34   89    1.46   35.37      0.8419E+01  0.5780E+01
   64   24    8    1.46   28.87      0.6871E+01  0.4877E+01
   57   39   25    1.46   29.35      0.6986E+01  0.5109E+01
   26   40   86    1.46   37.03      0.8814E+01  0.5927E+01
   22   36   92    1.46   29.56      0.7037E+01  0.6033E+01
   59   35   23    1.46   34.97      0.8324E+01  0.5132E+01
   67    1    6    1.47   40.17      0.9562E+01  0.3460E+01
   30   26   92    1.47   34.67      0.8252E+01  0.5613E+01
   20   74   33    1.47   30.26      0.7202E+01  0.4219E+01
   59   37   16    1.47   29.31      0.6976E+01  0.4725E+01
   30   38   84    1.47   46.66      0.1111E+02  0.5842E+01
   65   15   18    1.47   41.63      0.9909E+01  0.4447E+01
   56   30   45    1.47   36.77      0.8753E+01  0.4853E+01
   62   20   32    1.47   30.31      0.7215E+01  0.4630E+01
   48    8   76    1.47   47.58      0.1133E+02  0.5397E+01
   51    5   71    1.47   29.14      0.6935E+01  0.3821E+01
    3   79   27    1.47   37.67      0.8965E+01  0.4132E+01
   35   35   81    1.47   28.68      0.6826E+01  0.5653E+01
   29   39   84    1.47   50.08      0.1192E+02  0.6359E+01
   38   30   81    1.47   31.35      0.7463E+01  0.4646E+01
   56   42   21    1.47   33.24      0.7913E+01  0.5078E+01
   32   34   85    1.47   29.80      0.7094E+01  0.5433E+01
   36   64   34    1.47   30.21      0.7192E+01  0.4368E+01
   39   31   79    1.47   40.13      0.9552E+01  0.4460E+01
   34   24   89    1.47   31.03      0.7387E+01  0.4574E+01
   22   42   87    1.47   33.65      0.8009E+01  0.6308E+01
    5   79   26    1.47   30.61      0.7285E+01  0.3881E+01
   55   43   24    1.47   34.62      0.8240E+01  0.5274E+01
   65   19    7    1.47   37.61      0.8951E+01  0.5136E+01
   64   24    1    1.47   41.31      0.9833E+01  0.3436E+01
   15   43   90    1.47   52.09      0.1240E+02  0.6165E+01
   51   39   48    1.47   57.66      0.1372E+02  0.5061E+01
   52   28   58    1.47   31.55      0.7509E+01  0.4809E+01
   25   71   35    1.47   30.55      0.7272E+01  0.4231E+01
   12   78   25    1.47   38.17      0.9086E+01  0.4335E+01
   65   19    6    1.47   37.65      0.8962E+01  0.4977E+01
    5   53   83    1.47   38.27      0.9109E+01  0.5502E+01
   53   19   62    1.47   35.68      0.8493E+01  0.5430E+01
   13   39   94    1.47   51.76      0.1232E+02  0.5176E+01
   62   28   17    1.47   40.59      0.9662E+01  0.4995E+01
   22   34   93    1.47   32.42      0.7716E+01  0.6118E+01
   11   77   31    1.47   34.63      0.8243E+01  0.4159E+01
   32   70   20    1.47   47.18      0.1123E+02  0.4543E+01
   23   33   93    1.47   59.12      0.1407E+02  0.5830E+01
   56   18   55    1.47   30.73      0.7315E+01  0.5196E+01
   23   41   87    1.47   39.53      0.9409E+01  0.6240E+01
   10   78   27    1.47   36.33      0.8647E+01  0.4064E+01
   27   43   82    1.47   46.23      0.1100E+02  0.5920E+01
   18   74   35    1.47   41.44      0.9864E+01  0.4291E+01
   66    4   17    1.47   30.42      0.7241E+01  0.4608E+01
   13   47   87    1.47   65.06      0.1549E+02  0.6074E+01
   18   76   26    1.47   44.17      0.1051E+02  0.4341E+01
   64   20   17    1.47   76.58      0.1823E+02  0.5270E+01
   10   50   85    1.47   29.41      0.7000E+01  0.5327E+01
   54   18   60    1.47   40.61      0.9667E+01  0.5213E+01
   47    1   78    1.47   39.92      0.9501E+01  0.3842E+01
   45   55   33    1.47   38.19      0.9089E+01  0.4817E+01
   33   29   87    1.47   40.45      0.9627E+01  0.5925E+01
   17   77   22    1.47   36.16      0.8607E+01  0.4322E+01
   45    3   81    1.47   34.05      0.8105E+01  0.5750E+01
   55   43   23    1.47   30.06      0.7154E+01  0.4518E+01
   27   71   30    1.47   38.65      0.9198E+01  0.4323E+01
   15   47   86    1.47   32.14      0.7649E+01  0.5816E+01
   14   42   91    1.47   60.47      0.1439E+02  0.5700E+01
   46   56   25    1.47   30.18      0.7182E+01  0.2937E+01
   32   32   86    1.47   37.59      0.8947E+01  0.5996E+01
   26   38   87    1.47   65.41      0.1557E+02  0.5756E+01
   31   27   90    1.47   33.30      0.7925E+01  0.5675E+01
   54   42   31    1.47   38.63      0.9195E+01  0.4708E+01
   53   31   52    1.47   29.09      0.6924E+01  0.4457E+01
   62   22   28    1.47   30.33      0.7218E+01  0.4131E+01
   39   61   34    1.47   47.53      0.1131E+02  0.4921E+01
   66    4   16    1.47   28.81      0.6857E+01  0.4590E+01
   53   43   33    1.47   42.47      0.1011E+02  0.4288E+01
   53   23   59    1.47   51.98      0.1237E+02  0.4894E+01
   22   32   94    1.47   29.71      0.7071E+01  0.5641E+01
   66   12    4    1.47   32.64      0.7770E+01  0.3363E+01
   54   10   63    1.47   35.35      0.8415E+01  0.4959E+01
   29   69   33    1.47   37.00      0.8807E+01  0.4310E+01
   59   37   12    1.47   38.34      0.9125E+01  0.5050E+01
    1   53   83    1.47   30.88      0.7349E+01  0.3906E+01
   33   23   90    1.47   37.54      0.8935E+01  0.6186E+01
   37   31   81    1.47   44.19      0.1052E+02  0.5791E+01
   36   34   80    1.47   48.60      0.1157E+02  0.5842E+01
    4   46   90    1.47   43.40      0.1033E+02  0.5858E+01
   61   25   29    1.47   32.61      0.7761E+01  0.4324E+01
    3   45   91    1.47   29.80      0.7093E+01  0.5993E+01
   56   10   58    1.47   28.74      0.6842E+01  0.4515E+01
   63   25   13    1.47   30.79      0.7329E+01  0.4890E+01
   66    8   12    1.47   32.39      0.7710E+01  0.4615E+01
   54   46   17    1.47   42.56      0.1013E+02  0.5092E+01
   27   69   37    1.47   36.01      0.8572E+01  0.4514E+01
   29   37   85    1.47   30.31      0.7214E+01  0.5495E+01
   46    4   79    1.47   65.25      0.1553E+02  0.5753E+01
   12   76   33    1.47   29.76      0.7083E+01  0.3912E+01
   62   28   14    1.47   54.35      0.1294E+02  0.5168E+01
   32   30   87    1.47   77.18      0.1837E+02  0.6118E+01
   52   50   12    1.47   29.26      0.6965E+01  0.5200E+01
   28   38   85    1.47   30.24      0.7198E+01  0.5599E+01
   21   37   91    1.47   44.06      0.1049E+02  0.5717E+01
   43    7   83    1.47   28.93      0.6887E+01  0.5443E+01
   22   40   88    1.47   33.24      0.7913E+01  0.5930E+01
   61   31   14    1.48   57.48      0.1368E+02  0.5355E+01
   46   54   31    1.48   29.35      0.6986E+01  0.4567E+01
   30   28   90    1.48   49.34      0.1174E+02  0.5680E+01
   35   63   38    1.48   36.64      0.8720E+01  0.4436E+01
   60   30   25    1.48   31.87      0.7584E+01  0.4610E+01
   19   73   36    1.48   36.00      0.8568E+01  0.4073E+01
    6   80   15    1.48   31.36      0.7465E+01  0.3713E+01
   22   36   91    1.48   32.65      0.7770E+01  0.6241E+01
   61   29   20    1.48   42.29      0.1007E+02  0.4987E+01
   29   69   32    1.48   37.26      0.8867E+01  0.4578E+01
   23   39   88    1.48   54.03      0.1286E+02  0.6190E+01
   36   24   86    1.48   52.75      0.1255E+02  0.5827E+01
   56   16   55    1.48   37.26      0.8869E+01  0.5113E+01
   55   13   59    1.48   30.55      0.7271E+01  0.5101E+01
   53   17   62    1.48   35.44      0.8434E+01  0.4914E+01
    8   48   87    1.48   29.74      0.7080E+01  0.5832E+01
   19   37   92    1.48   30.93      0.7362E+01  0.6390E+01
   52   24   60    1.48   28.79      0.6853E+01  0.4899E+01
   38   30   80    1.48   29.24      0.6960E+01  0.6108E+01
   63   21   21    1.48   38.62      0.9192E+01  0.4366E+01
   20   74   30    1.48   32.69      0.7781E+01  0.4255E+01
   26   30   92    1.48   28.47      0.6777E+01  0.5641E+01
   51   51   14    1.48   38.54      0.9174E+01  0.4718E+01
   17   37   93    1.48   49.06      0.1168E+02  0.6448E+01
   40   24   81    1.48   36.54      0.8696E+01  0.5318E+01
   26   42   83    1.48   34.01      0.8094E+01  0.5679E+01
   36   62   38    1.48   36.88      0.8777E+01  0.4527E+01
    7   45   90    1.48   58.30      0.1388E+02  0.5868E+01
   55   31   45    1.48   32.94      0.7841E+01  0.4331E+01
   27   69   36    1.48   34.21      0.8142E+01  0.4581E+01
   45   55   31    1.48   46.92      0.1117E+02  0.4500E+01
   56   38   29    1.48   29.47      0.7014E+01  0.4735E+01
   41    9   85    1.48   34.35      0.8177E+01  0.5752E+01
   63   23   16    1.48   34.74      0.8269E+01  0.5064E+01
   62   26   18    1.48   39.95      0.9510E+01  0.5237E+01
   31   67   34    1.48   37.16      0.8844E+01  0.4430E+01
   25   31   92    1.48   45.88      0.1092E+02  0.5805E+01
   28   32   89    1.48   38.42      0.9144E+01  0.5462E+01
   51   51   13    1.48   35.64      0.8482E+01  0.4465E+01
   19   77   12    1.48   38.41      0.9143E+01  0.2749E+01
   54    6   63    1.48   33.24      0.7912E+01  0.4897E+01
   33   35   82    1.48   41.52      0.9883E+01  0.5741E+01
   51   17   66    1.48   47.54      0.1131E+02  0.4834E+01
   42   58   32    1.48   47.87      0.1139E+02  0.4932E+01
   21   35   92    1.48   29.10      0.6927E+01  0.5865E+01
   55   29   47    1.48   38.50      0.9163E+01  0.4619E+01
    6   78   27    1.48   30.59      0.7280E+01  0.3888E+01
   43   19   79    1.48   35.64      0.8482E+01  0.5613E+01
   21   39   89    1.48   56.94      0.1355E+02  0.6562E+01
   47    9   76    1.48   39.55      0.9414E+01  0.5261E+01
   42   22   79    1.48   40.90      0.9734E+01  0.5352E+01
   62   28   10    1.48   34.53      0.8219E+01  0.4574E+01
   50   46   36    1.48   34.22      0.8145E+01  0.4015E+01
   44   56   31    1.48   29.85      0.7104E+01  0.4817E+01
   63   23   15    1.48   37.74      0.8983E+01  0.4789E+01
    6   50   85    1.48   42.74      0.1017E+02  0.5437E+01
   24   72   30    1.48   53.32      0.1269E+02  0.4844E+01
   28   36   86    1.48   40.87      0.9728E+01  0.5781E+01
   31   29   88    1.48   40.76      0.9703E+01  0.5657E+01
   61   31   10    1.48   28.35      0.6749E+01  0.4770E+01
   57   15   52    1.48   42.46      0.1011E+02  0.4956E+01
   49   53   17    1.48   29.28      0.6968E+01  0.4688E+01
   60   30   23    1.48   36.32      0.8644E+01  0.5041E+01
    5   51   84    1.48   31.66      0.7534E+01  0.3861E+01
   66    2   11    1.48   36.35      0.8653E+01  0.3373E+01
   36   30   82    1.48   54.73      0.1303E+02  0.5726E+01
   54   44   22    1.48   52.17      0.1242E+02  0.5212E+01
   54    4   63    1.48   34.79      0.8280E+01  0.5269E+01
   11   41   92    1.48   41.76      0.9938E+01  0.5950E+01
   15   47   85    1.48   49.95      0.1189E+02  0.5695E+01
    2   78   28    1.48   51.64      0.1229E+02  0.4114E+01
   50   44   40    1.48   33.28      0.7922E+01  0.4381E+01
    4   44   91    1.48   54.58      0.1299E+02  0.5978E+01
   25   39   86    1.48   41.91      0.9975E+01  0.6168E+01
   26   38   86    1.48   62.36      0.1484E+02  0.5485E+01
   45    9   79    1.48   43.19      0.1028E+02  0.5625E+01
   56   18   53    1.48   34.78      0.8277E+01  0.4922E+01
   66    6    7    1.48   40.65      0.9676E+01  0.2586E+01
   31   27   89    1.48   33.71      0.8024E+01  0.6117E+01
   54   46   12    1.48   34.21      0.8143E+01  0.4826E+01
   52    6   67    1.48   29.47      0.7014E+01  0.3879E+01
   53   25   56    1.48   51.16      0.1218E+02  0.5213E+01
   35   25   86    1.48   32.88      0.7826E+01  0.5854E+01
   55   43   18    1.48   76.51      0.1821E+02  0.5229E+01
   55   19   55    1.48   29.99      0.7137E+01  0.4861E+01
   52   48   19    1.48   50.28      0.1197E+02  0.4947E+01
   56   16   54    1.48   36.93      0.8790E+01  0.4727E+01
   39   27   80    1.48   36.76      0.8751E+01  0.6171E+01
   33   23   89    1.48   49.43      0.1177E+02  0.6141E+01
   65   11   15    1.48   32.97      0.7848E+01  0.4544E+01
   46   10   77    1.48   32.98      0.7849E+01  0.5561E+01
   52   24   59    1.48   34.30      0.8164E+01  0.5286E+01
   12   46   87    1.48   28.37      0.6752E+01  0.5881E+01
   33   33   83    1.48   43.90      0.1045E+02  0.5675E+01
   12   48   85    1.48   38.65      0.9198E+01  0.5724E+01
    4   48   87    1.48   49.85      0.1186E+02  0.5482E+01
   39   13   86    1.48   29.97      0.7134E+01  0.6035E+01
   25   71   31    1.48   35.65      0.8486E+01  0.4306E+01
   65   13   11    1.48   40.12      0.9548E+01  0.4721E+01
    6   54   80    1.48   30.05      0.7153E+01  0.5271E+01
   61   31    6    1.48   30.93      0.7361E+01  0.4821E+01
   24   44   82    1.49   40.34      0.9601E+01  0.6420E+01
   48   12   73    1.49   42.78      0.1018E+02  0.5272E+01
   60   22   35    1.49   28.97      0.6894E+01  0.4147E+01
   39   25   81    1.49   66.12      0.1574E+02  0.5639E+01
   11   43   90    1.49   31.42      0.7478E+01  0.5890E+01
   18   44   86    1.49   37.14      0.8840E+01  0.5676E+01
   36   20   87    1.49   46.31      0.1102E+02  0.5973E+01
   39   21   83    1.49   28.81      0.6856E+01  0.5645E+01
   18   48   82    1.49   39.20      0.9331E+01  0.5892E+01
   18   38   91    1.49   31.79      0.7568E+01  0.5706E+01
   15   77   20    1.49   28.97      0.6896E+01  0.3946E+01
   43   55   36    1.49   30.37      0.7228E+01  0.4534E+01
   15   41   90    1.49   48.54      0.1155E+02  0.6075E+01
   44   16   78    1.49   28.93      0.6886E+01  0.5404E+01
   59   35   13    1.49   29.30      0.6974E+01  0.4814E+01
   40   20   82    1.49   82.09      0.1954E+02  0.6136E+01
    7   79   17    1.49   28.51      0.6787E+01  0.3598E+01
   16   76   24    1.49   32.80      0.7807E+01  0.4341E+01
   56    6   57    1.49   49.56      0.1180E+02  0.5003E+01
   24   34   90    1.49   49.87      0.1187E+02  0.5884E+01
   46   20   73    1.49   33.45      0.7962E+01  0.5370E+01
   39   61   30    1.49   33.51      0.7977E+01  0.4725E+01
   38   16   86    1.49   57.78      0.1375E+02  0.5846E+01
   32   34   83    1.49   48.73      0.1160E+02  0.5836E+01
   53   33   47    1.49   30.94      0.7364E+01  0.4403E+01
   48    6   74    1.49   28.39      0.6758E+01  0.3812E+01
   55    1   60    1.49   38.40      0.9140E+01  0.5664E+01
   13   51   81    1.49   40.14      0.9554E+01  0.5071E+01
   51   47   27    1.49   33.01      0.7857E+01  0.3070E+01
   28   70   27    1.49   41.44      0.9863E+01  0.4643E+01
   59   35   12    1.49   31.21      0.7429E+01  0.4817E+01
   22   42   85    1.49   28.51      0.6787E+01  0.5975E+01
   32   26   88    1.49   40.78      0.9707E+01  0.5822E+01
   31   31   86    1.49   60.87      0.1449E+02  0.6057E+01
   41    9   84    1.49   28.79      0.6853E+01  0.5608E+01
   44   18   77    1.49   36.03      0.8575E+01  0.5509E+01
   32   24   89    1.49   39.09      0.9305E+01  0.5670E+01
   53   21   58    1.49   30.95      0.7367E+01  0.5053E+01
   47    1   76    1.49   32.57      0.7752E+01  0.3747E+01
   54   44   19    1.49   47.00      0.1119E+02  0.5049E+01
   17   75   27    1.49   33.80      0.8044E+01  0.4540E+01
   54    4   62    1.49   50.59      0.1204E+02  0.5652E+01
   28   32   88    1.49   41.28      0.9825E+01  0.5761E+01
   19   75   23    1.49   34.44      0.8197E+01  0.4170E+01
   65    7   16    1.49   35.08      0.8351E+01  0.4535E+01
   42   22   78    1.49   47.17      0.1123E+02  0.5841E+01
   29   67   36    1.49   52.97      0.1261E+02  0.4301E+01
   15   43   88    1.49   69.33      0.1650E+02  0.6392E+01
   50   14   68    1.49   37.80      0.8996E+01  0.5179E+01
   33   67   25    1.49   30.70      0.7308E+01  0.4313E+01
   38   62   29    1.49   44.14      0.1051E+02  0.4789E+01
   17   43   87    1.49   56.13      0.1336E+02  0.5643E+01
   37   23   84    1.49   35.31      0.8405E+01  0.5364E+01
   55   23   51    1.49   32.77      0.7799E+01  0.4587E+01
   36   16   88    1.49   33.22      0.7907E+01  0.5752E+01
   34   66   26    1.49   32.41      0.7713E+01  0.4340E+01
   63   19   19    1.49   34.80      0.8283E+01  0.4352E+01
    6   50   84    1.49   32.68      0.7779E+01  0.5301E+01
   53   39   37    1.49   36.49      0.8686E+01  0.4152E+01
   59   31   24    1.49   34.32      0.8169E+01  0.4753E+01
   54   44   18    1.49   47.31      0.1126E+02  0.4874E+01
   40   62   20    1.49   28.77      0.6847E+01  0.4651E+01
   23   33   91    1.49   44.48      0.1059E+02  0.5611E+01
   43   13   80    1.49   31.27      0.7444E+01  0.5989E+01
   29   25   91    1.49   38.91      0.9261E+01  0.5421E+01
   17   47   83    1.49   32.73      0.7791E+01  0.6176E+01
    6   48   86    1.49   33.12      0.7882E+01  0.5450E+01
    9   43   90    1.49   51.08      0.1216E+02  0.5696E+01
   25   71   29    1.49   45.67      0.1087E+02  0.4137E+01
   38   32   77    1.49   54.25      0.1291E+02  0.5605E+01
   15   47   84    1.49   58.02      0.1381E+02  0.5709E+01
   37   63   28    1.49   32.25      0.7676E+01  0.4521E+01
   65    3   17    1.49   32.54      0.7745E+01  0.4695E+01
   55   27   47    1.49   31.41      0.7477E+01  0.4434E+01
   22   38   88    1.49   30.34      0.7222E+01  0.6133E+01
   57   37   21    1.49   32.66      0.7773E+01  0.4719E+01
   64   14   17    1.49   44.65      0.1063E+02  0.4740E+01
   42   14   81    1.49   55.36      0.1318E+02  0.5855E+01
   40   16   83    1.49   69.06      0.1644E+02  0.6070E+01
   44   54   34    1.49   36.40      0.8664E+01  0.4957E+01
   18   74   29    1.49   43.62      0.1038E+02  0.4757E+01
   46    4   77    1.49   51.33      0.1222E+02  0.5837E+01
   25   35   88    1.49   30.65      0.7295E+01  0.5499E+01
   60   32   10    1.49   36.33      0.8647E+01  0.5025E+01
   55   21   52    1.49   49.74      0.1184E+02  0.4980E+01
   54   36   38    1.49   34.11      0.8118E+01  0.4413E+01
   64   12   19    1.49   29.23      0.6957E+01  0.4215E+01
   54   32   44    1.49   36.52      0.8692E+01  0.4484E+01
   29   33   86    1.49   58.10      0.1383E+02  0.5593E+01
   33   23   88    1.49   41.98      0.9993E+01  0.5604E+01
   36   28   82    1.49   36.59      0.8708E+01  0.5721E+01
   65    9   11    1.49   28.75      0.6842E+01  0.4506E+01
   28   28   90    1.49   45.49      0.1083E+02  0.5810E+01
    7   53   80    1.50   38.75      0.9223E+01  0.5333E+01
   52   12   64    1.50   36.20      0.8616E+01  0.5271E+01
   44   10   79    1.50   34.84      0.8292E+01  0.5400E+01
   52   44   29    1.50   33.25      0.7913E+01  0.4805E+01
   46    2   77    1.50   37.56      0.8941E+01  0.3909E+01
   52   34   47    1.50   29.05      0.1339E+02  0.4916E+01
   19   45   83    1.50   49.84      0.2297E+02  0.6211E+01
   46   14   74    1.50   33.20      0.1530E+02  0.5581E+01
   18   40   88    1.50   31.85      0.1468E+02  0.6430E+01
   60   30   14    1.50   30.49      0.1405E+02  0.4961E+01
    9   43   89    1.50   32.11      0.1480E+02  0.6290E+01
   35   21   86    1.50   30.75      0.1417E+02  0.5662E+01
   16   44   85    1.51   34.16      0.1575E+02  0.6118E+01
   36   62   31    1.51   29.01      0.1337E+02  0.4952E+01
   44   18   75    1.51   32.06      0.1478E+02  0.5612E+01
   35   29   81    1.51   29.29      0.1350E+02  0.5872E+01
   53   21   55    1.51   29.17      0.1344E+02  0.5244E+01
   18   36   90    1.52   33.91      0.1563E+02  0.6100E+01
   58   32   19    1.52   30.96      0.1427E+02  0.4973E+01
   34   64   26    1.52   28.61      0.1318E+02  0.5088E+01
   24   36   85    1.53   33.03      0.1522E+02  0.6242E+01
   10   40   89    1.53   29.56      0.1362E+02  0.5157E+01
   42   14   77    1.54   30.69      0.1414E+02  0.5803E+01
   44    4   76    1.54   28.69      0.1322E+02  0.5602E+01
   20   36   87    1.54   32.76      0.1510E+02  0.6125E+01
   21   35   87    1.54   33.76      0.1556E+02  0.6562E+01
   42    8   78    1.54   30.43      0.1402E+02  0.5795E+01
   53   39   24    1.54   31.27      0.1582E+02  0.5131E+01
   40   10   80    1.55   34.36      0.1738E+02  0.6086E+01
   18   44   80    1.55   29.34      0.1484E+02  0.6097E+01
   51   13   59    1.55   32.30      0.1634E+02  0.5393E+01
   39   17   78    1.56   31.11      0.1573E+02  0.5675E+01
   12   44   82    1.56   34.80      0.1760E+02  0.6083E+01
   51   41   23    1.57   33.33      0.1686E+02  0.5280E+01
   33   23   81    1.58   35.66      0.1804E+02  0.6016E+01
   34   24   79    1.58   29.94      0.1514E+02  0.6153E+01
   53   35   24    1.58   29.31      0.1483E+02  0.5025E+01
   37   13   78    1.61   30.03      0.1751E+02  0.5685E+01
   54   28   25    1.62   30.42      0.1775E+02  0.5202E+01
   42   16   68    1.63   31.72      0.1850E+02  0.5596E+01
   53   29   23    1.64   30.81      0.1797E+02  0.5322E+01
   22   36   77    1.65   29.04      0.1694E+02  0.6421E+01

 NUMBER OF UNIQUE ALIEN REFLECTIONS WITH A Z-SCORE ABOVE LIMIT      1324
 (ALIENS ABOVE LIMIT (REJECT_ALIEN=      20.0) ARE MARKED INVALID)

 NUMBER OF REFLECTION RECORDS ON OUTPUT FILE "XDS_ASCII.HKL"       79478
 NUMBER OF ACCEPTED OBSERVATIONS (INCLUDING SYSTEMATIC ABSENCES)   77705
 NUMBER OF REJECTED MISFITS & ALIENS (marked by -1*SIGMA(IOBS))     1773


 cpu time used                 10.9 sec
 elapsed wall-clock time        1.4 sec
