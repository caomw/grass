# nc2008/grass7 mapset
g.copy vect=elev_lid792_bepts,lidar_test
v.build lidar_test
g.region n=221230 s=220816 w=639090 e=639530 res=0.5 -p
CMD="v.surf.rst in=lidar_test -z elev=omp_test.rst --o"
time $CMD

valgrind --tool=callgrind --trace-children=yes $CMD
kcachegrind callgrind.out.1196


x% of module time is spent in fn()



 r.out.ascii omp_test.rst.g7omp6b dp=6 | md5sum
32d2890afa57354d0d0e4a69b507e81e


time $CMD
=========

orig serial run:
res=2
real    0m46.088s
user    0m46.027s
sys     0m0.064s
res=0.5
real    1m1.390s
user    1m1.312s
sys     0m0.080s

--raster map not found?


