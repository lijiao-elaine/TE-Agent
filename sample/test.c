#include <stdio.h>
#include <unistd.h>  // 用于Linux系统的sleep函数
#include <string.h>  // 用于处理字符串
#include <time.h>

// 定义日志文件路径（宏定义方便后续修改）
#define LOG_FILE_PATH "/home/lijiao/work/TE-Agent/sample/full_process_test.log"
#define TIME_BUF_SIZE 64

int main(int argc, char *argv[]) {
    // 打开日志文件："a+" 表示追加模式（新增内容写在文件末尾）+ 文本模式
    FILE *log_file = fopen(LOG_FILE_PATH, "w+");
    if (log_file == NULL) {
        // 文件打开失败时，打印错误到标准错误流（应急提示）
        perror("Failed to open log file");
        return 1;  // 非0退出码表示程序异常
    }

    // 获取并写入当前时间
    char time_buf[TIME_BUF_SIZE];
    time_t current_time = time(NULL);  // 获取当前时间戳（秒级）
    struct tm *local_time = localtime(&current_time);  // 转换为本地时间结构体
    if (local_time != NULL) {
        // 格式化时间：[年-月-日 时:分:秒] Program started
        strftime(time_buf, sizeof(time_buf), "[%Y-%m-%d %H:%M:%S] Program started\n", local_time);
        fprintf(log_file, "%s", time_buf);  // 写入时间日志
        fflush(log_file);  // 刷新缓冲区，确保时间日志实时写入
    } else {
        // 时间获取失败时的容错处理
        const char *time_error = "[Unknown Time] Failed to get current time\n";
        fprintf(log_file, "%s", time_error);
        fflush(log_file);
    }

    //sleep(8);  // 延迟8秒

    // 第一句日志：包含入参信息
    if (argc > 1) {
        fprintf(log_file, "start test with input parameter: %s\n", argv[1]);
    } else {
        fprintf(log_file, "start test without input parameter\n");
    }
    fflush(log_file);  // 刷新缓冲区，确保日志实时写入

    // 第二句日志：启动成功提示
    fprintf(log_file, "--------test epoll creat success----------\n");
    fflush(log_file);

    // 无限循环输出日志，每秒一次
    for (int i = 0; i >= 0; i++) {
        if (argc > 1) {
            fprintf(log_file, "start test with input parameter: %s, number: %d\n", argv[1], i);
        } else {
            // 处理无参数场景，避免argv[1]空指针异常
            fprintf(log_file, "start test without input parameter, number: %d\n", i);
        }
        fflush(log_file);  // 每次循环刷新缓冲区
        sleep(1);
    }

    // 理论上无限循环不会执行到这里，但仍规范关闭文件
    fclose(log_file);
    return 0;
}