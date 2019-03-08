@echo off

echo Running robocopy
set working_dir_1="C:\csim\Rundirs"
set backup_dir_1="\\lasp-store\csim\raw_files"

robocopy %working_dir_1% %backup_dir_1% /z /e /mir 

echo Done!
