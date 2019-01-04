@echo off
python "C:\data-processing\cube-ds\main.py"

echo Running robocopy
set working_dir_1="C:\csim"
set backup_dir_1="\\lasp-store\projects\Phase_Development\CSIM FD\Computer Backup\WinD3782\csim"

set working_dir_2="C:\data-processing"
set backup_dir_2="\\lasp-store\projects\Phase_Development\CSIM FD\Computer Backup\WinD3782\data-processing"

robocopy %working_dir_1% %backup_dir_1% /z /e /mir 
robocopy %working_dir_2% %backup_dir_2% /z /e /mir 

echo Starting idl processing
idl -e csim_fd_parse_raw_record_files

pause