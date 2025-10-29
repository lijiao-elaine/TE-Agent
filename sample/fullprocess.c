#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>

#define LOG_FILE_PATH "/home/lijiao/work/TE-Agent/sample/full_process_fullprocess.log"
#define BUF_SIZE 256

int main(int argc, char *argv[]) {
    int log_fd = open(LOG_FILE_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (log_fd == -1) {
        perror("Failed to open log file (fd)");
        return 1;
    }

    // 获取并写入当前时间
    char time_buf[BUF_SIZE];
    time_t current_time = time(NULL);  // 获取当前时间戳
    struct tm *local_time = localtime(&current_time);  // 转换为本地时间
    if (local_time != NULL) {
        // 格式化时间：年-月-日 时:分:秒
        strftime(time_buf, sizeof(time_buf), "[%Y-%m-%d %H:%M:%S] Program started\n", local_time);
        // 写入时间日志
        write(log_fd, time_buf, strlen(time_buf));
    } else {
        const char *time_error = "[Unknown Time] Failed to get current time\n";
        write(log_fd, time_error, strlen(time_error));
    }

    char buf[BUF_SIZE];
    int len;

    // 第一句日志：校验格式化结果
    if (argc > 1) {
        len = snprintf(buf, sizeof(buf), "start full process with input parameter: %s\n", argv[1]);
    } else {
        len = snprintf(buf, sizeof(buf), "start full process without input parameter\n");
    }
    // 校验 len 是否在合理范围内，避免无效数据
    if (len > 0 && len < BUF_SIZE) {
        write(log_fd, buf, len);
    } else {
        const char *error_msg = "Failed to format log string\n";
        write(log_fd, error_msg, strlen(error_msg));
    }

    // 第二句日志：同样增加校验
    len = snprintf(buf, sizeof(buf), "--------start full process success----------\n");
    if (len > 0 && len < BUF_SIZE) {
        write(log_fd, buf, len);
    }

    // 循环日志：增加校验
    for (int i = 0; i >= 0; i++) {
        if (argc > 1) {
            len = snprintf(buf, sizeof(buf), "start full process with input parameter: %s, number: %d\n", argv[1], i);
        } else {
            len = snprintf(buf, sizeof(buf), "start full process without input parameter, number: %d\n", i);
        }
        if (len > 0 && len < BUF_SIZE) {
            write(log_fd, buf, len);
        }
        sleep(1);
    }

    close(log_fd);
    return 0;
}