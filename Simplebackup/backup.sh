#!/bin/bash
#Simple script that aggregates stuff on a linux box and scp it to another box for backup .
#just run this as a cronjob or whenever you want to backup.

#This will check the wlan0 (default) interface on which SSID its connected to.

ssid=$(sudo iwconfig wlan0 | grep ESSID | awk '{print $4}' | awk -F: '{print $2}' | tr -d '"'})

#setting up some variables. 
homessid=“[YOUR HOME NETWORK]“
homeboxip=“[TARGET IP ADDRESS]“
backupdate=`date +%Y-%m-%d`

#if both the source and target are on the same SSID then
if [ "$ssid" == "$homessid" ] 
then

#Adjust the following to your needs. 

#create backup directory and copy files over
sudo rm -rf /home/chip/backup/*
sudo mkdir /home/chip/backup/$backupdate/
sudo cp -r /home/chip/scripts/* /home/chip/backup/$backupdate/
sudo cp /usr/share/pocket-home/config.json /home/chip/backup/$backupdate/
sudo cp /home/chip/.bashrc /home/chip/backup/$backupdate/bashrc
sudo cp /home/chip/.profile /home/chip/backup/$backupdate/profile
sudo cp /home/chip/dumps/* /home/chip/backup/$backupdate/

#scp to the destination box. 

sudo scp -r  /home/chip/backup/$backupdate/  [username]@$homeboxip:/HackerChip/Backups/

fi
