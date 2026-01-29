from utils.word_report_filler import WordReportFiller

if __name__ == "__main__":
    # WordReportFiller().find_headings("/home/micros/测试执行记录/附录A--测试执行记录标准版.docx")
    test_case_word_file = "/home/micros/测试执行记录/附录A--测试执行记录标准版.docx"
    test_outline_word_file = "/home/micros/测试执行记录/测试大纲/2025年度节点考核测试大纲标准版.docx"
    test_case_map = WordReportFiller().get_test_case(test_case_word_file, test_outline_word_file)

    # print()
