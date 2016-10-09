#!/bin/bash 
if [ ! -d converted/ ] 
then 
 mkdir converted; 
fi;
for i in ./*.wav
 do sox -S "$i" -r 8k -b 16 -c 1 -e signed-integer "converted/$i";
done;
