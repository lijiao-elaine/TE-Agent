#include <stdio.h>
#include <unistd.h>  // 用于Linux系统的sleep函数

int main(int argc, char *argv[]) {
    // 打印包含入参的第一句话
    // 检查是否提供了参数
    if (argc > 1) {
        printf("start main with input parameter: %s\n", argv[1]);
    } else {
        printf("start main without input parameter\n");
    }

    // 打印第二句话
    printf("--------epoll creat success----------\n");

    // 无限循环保持进程不退出，每秒休眠一次以减少CPU占用
    for (int i=0; i>=0; i++) {
	printf("start main with input parameter: %s, number: %d\n", argv[1], i);
        sleep(1);
    }

    return 0;
}

