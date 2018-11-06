#! /usr/bin/env python
print 'Antenna Length Calculator for SHR789 Antenna'
Mhz=float(input ("Input target frequency Mhz:"))
khzFreq=int(Mhz*1000)
if khzFreq < 95000 or khzFreq > 1100000:
        print 'not in range for this antenna'
        
elif  khzFreq > 95000 and khzFreq < 300000:
        AntLen=float(299792458/khzFreq*0.25/10)
        print 'Antenna length should be:',AntLen,'cm'
elif khzFreq >300000 and khzFreq < 1100000:
        AntLen=float(299792458/khzFreq*0.5/10)
        print 'Antenna length should be:',AntLen,'cm'
