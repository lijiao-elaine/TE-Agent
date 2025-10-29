#!/bin/bash

# 明确指定 UTF-8 编码，强制程序输出为 UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_CTYPE=en_US.UTF-8

# 提前创建日志文件，确保权限正确（避免程序创建时的权限问题）
LOG_FILE_FULLPROCESS="/home/lijiao/work/TE-Agent/sample/full_process_fullprocess.log"
LOG_FILE_TEST="/home/lijiao/work/TE-Agent/sample/full_process_test.log"

# 创建日志文件并设置权限为 644（可读可写）
touch $LOG_FILE_FULLPROCESS 
chmod 644 $LOG_FILE_FULLPROCESS 
touch $LOG_FILE_TEST
chmod 644  $LOG_FILE_TEST

#修改被测程序的权限
BIN_FULLPROCESS="/home/lijiao/work/TE-Agent/sample/fullprocess"
BIN_TEST="/home/lijiao/work/TE-Agent/sample/test"
chmod +x $BIN_FULLPROCESS
chmod +x $BIN_TEST

# 后台启动main程序，输出重定向到main.log
#nohup /home/lijiao/work/TE-Agent/sample/fullprocess > /home/lijiao/work/TE-Agent/sample/full_process_fullprocess.log 2>&1 &
#nohup stdbuf -oL -eL /home/lijiao/work/TE-Agent/sample/fullprocess fullprocess > /home/lijiao/work/TE-Agent/sample/full_process_fullprocess.log 2>&1 &
nohup /home/lijiao/work/TE-Agent/sample/fullprocess fullprocess > /dev/null 2>&1 &
echo "fullprocess程序已启动，PID: $!"  # $! 表示刚启动进程的PID

# 后台启动test程序，输出重定向到test.log
#nohup stdbuf -oL -eL /home/lijiao/work/TE-Agent/sample/test test > /home/lijiao/work/TE-Agent/sample/full_process_test.log 2>&1 &
nohup  /home/lijiao/work/TE-Agent/sample/test test > /dev/null 2>&1 &
echo "test程序已启动，PID: $!"

