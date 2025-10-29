#!/bin/bash

# 杀掉fullprocess程序（忽略不存在的进程错误）
#if pkill -f "fullprocess"; then
#  echo "fullprocess程序已终止"
#else
#  echo "fullprocess程序未运行"
#fi

# 杀掉test程序（忽略不存在的进程错误）
#if pkill -f "test"; then
#  echo "test程序已终止"
#else
#  echo "test程序未运行"
#fi

#!/bin/bash

#!/bin/bash

# 精确匹配fullprocess进程（通过绝对路径）
FULLPROCESS_PATH="/home/lijiao/work/TE-Agent/sample/fullprocess fullprocess"  # 替换为实际路径
if pkill -f "^${FULLPROCESS_PATH}$"; then
  echo "fullprocess程序已终止"
else
  echo "fullprocess程序未运行"
fi

# 精确匹配test进程（通过绝对路径）
TEST_PATH="/home/lijiao/work/TE-Agent/sample/test test"  # 替换为test程序的实际路径
if pkill -f "^${TEST_PATH}$"; then
  echo "test程序已终止"
else
  echo "test程序未运行"
fi

#echo "test程序和fullprocess程序未执行终止操作"
