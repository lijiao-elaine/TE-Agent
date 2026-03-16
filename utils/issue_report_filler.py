from docx import Document
from docx.table import Table
from docx.shared import Pt, RGBColor, Twips, Inches
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
import shutil
import sys

# 导入图片插入函数
from utils.word_report_filler import WordReportFiller

class IssueReportFiller:
    """处理失败测试用例向软件问题报告单的填充"""

    def __init__(self, config_manager):
        """
        初始化问题报告单填充器
        :param config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.issue_counter = 0  # 问题计数器，用于生成问题标识
        self._word_doc_cache = None  # Word文档缓存
        self._word_doc_path = None   # 缓存的文档路径

    def _get_word_doc(self) -> Document:
        """
        获取测试用例Word文档对象（使用缓存）
        :return: Word文档对象
        """
        # 从配置中获取原始Word文档路径（merged_document.docx）
        word_path = self.config_manager.get_original_word_file()
        
        # 如果路径变了或者缓存不存在，重新加载
        if self._word_doc_cache is None or self._word_doc_path != word_path:
            if os.path.exists(word_path):
                self._word_doc_cache = Document(word_path)
                self._word_doc_path = word_path
            else:
                # 尝试使用模板路径
                template_path = "template/merged_document.docx"
                if os.path.exists(template_path):
                    self._word_doc_cache = Document(template_path)
                    self._word_doc_path = template_path
                else:
                    self._word_doc_cache = None
                    self._word_doc_path = None
        
        return self._word_doc_cache

    def _find_case_table_in_word(self, doc: Document, case_id: str) -> Table:
        """
        在Word文档中查找对应用例的表格
        :param doc: Word文档对象
        :param case_id: 测试用例ID
        :return: 匹配的表格对象
        """
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = "\n".join([para.text for para in cell.paragraphs]).strip()
                    if case_id in cell_text:
                        return table
        return None

    def _extract_case_info_from_word(self, case_id: str) -> Dict[str, str]:
        """
        从Word文档中提取用例基本信息
        提取用例名称、用例标识（ID）、所属模块
        :param case_id: 测试用例ID（用于定位表格）
        :return: 包含 case_name, case_id, module 的字典
        """
        result = {
            "case_name": "",
            "case_id": "",
            "module": ""
        }
        
        doc = self._get_word_doc()
        if doc is None:
            print(f"[WARN] 无法加载Word文档，无法提取用例信息")
            return result
        
        # 查找对应用例的表格
        table = self._find_case_table_in_word(doc, case_id)
        if table is None:
            print(f"[WARN] 在Word文档中未找到用例 {case_id} 的表格")
            return result
        
        # 遍历表格查找用例名称和标识
        for row in table.rows:
            cells = row.cells
            if len(cells) < 9:
                continue
            
            first_cell_text = cells[0].text.strip()
            
            # 查找"测试用例名称"行（第1行，索引0）
            if first_cell_text == "测试用例名称":
                # 用例名称在第3列（索引2）
                result["case_name"] = cells[2].text.strip()
                # 用例ID在第9列（索引8）
                result["case_id"] = cells[8].text.strip()
                
                # 从用例ID中提取模块：第三个下划线之后、第四个下划线之前的部分
                # 例如：XXX_TEST_001_Observation_O1 -> Observation
                if result["case_id"]:
                    parts = result["case_id"].split('_')
                    if len(parts) >= 4:
                        result["module"] = parts[3]
                break
        
        return result

    def _extract_steps_from_word(self, case_id: str) -> List[Dict[str, str]]:
        """
        从Word文档中提取测试步骤信息
        提取每个步骤的"输入及操作"和"期望结果与评估标准"
        :param case_id: 测试用例ID
        :return: 步骤列表，每个步骤包含 input_action 和 expected_result
        """
        steps = []
        doc = self._get_word_doc()
        
        if doc is None:
            print(f"[WARN] 无法加载Word文档，将从JSON提取步骤信息")
            return steps
        
        # 查找对应用例的表格
        table = self._find_case_table_in_word(doc, case_id)
        if table is None:
            print(f"[WARN] 在Word文档中未找到用例 {case_id} 的表格")
            return steps
        
        # 查找"测试步骤"区域
        steps_start_row = -1
        header_row_idx = -1
        
        for row_idx, row in enumerate(table.rows):
            first_cell_text = row.cells[0].text.strip() if row.cells else ""
            # 找到"序号"列标题行，这是步骤数据的表头
            if first_cell_text == "序号":
                header_row_idx = row_idx
                steps_start_row = row_idx + 1
                break
        
        if steps_start_row == -1:
            print(f"[WARN] 在表格中未找到步骤数据起始行")
            return steps
        
        # 提取步骤数据
        for row_idx in range(steps_start_row, len(table.rows)):
            row = table.rows[row_idx]
            cells = row.cells
            
            if len(cells) < 3:
                continue
            
            # 第一列是序号，如果不是数字则可能是其他内容，跳过
            seq_num = cells[0].text.strip()
            if not seq_num.isdigit():
                continue
            
            # 提取"输入及操作"（第2列，索引1）
            # 由于单元格合并，需要获取所有相关单元格的文本
            input_action = ""
            if len(cells) > 1:
                input_action = "\n".join([para.text for para in cells[1].paragraphs]).strip()
            
            # 提取"期望结果与评估标准"（第6列，索引5，考虑到合并）
            expected_result = ""
            if len(cells) > 5:
                expected_result = "\n".join([para.text for para in cells[5].paragraphs]).strip()
            
            if input_action or expected_result:
                steps.append({
                    "seq": int(seq_num),
                    "input_action": input_action,
                    "expected_result": expected_result
                })
        
        return steps

    def _generate_issue_id(self, case_id: str) -> str:
        """
        生成问题标识
        格式: 用例标识第三个下划线后的所有内容-当前日期-序号
        例如: XXX_TEST_001_Observation_O1 -> Observation_O1-20260311-001
        :param case_id: 测试用例ID
        :return: 问题标识
        """
        self.issue_counter += 1
        date_str = datetime.now().strftime("%Y%m%d")
        # 提取第三个下划线后的所有内容
        parts = case_id.split('_')
        if len(parts) > 3:
            # 取第4个及之后的所有部分（索引3开始）
            suffix = '_'.join(parts[3:])
        elif len(parts) == 3:
            suffix = parts[2]
        else:
            suffix = case_id  # 如果不足3部分，使用完整ID
        return f"{suffix}-{date_str}-{self.issue_counter:03d}"

    def _extract_case_info(self, case_result: Dict[str, Any]) -> Dict[str, str]:
        """
        从测试结果中提取用例信息
        :param case_result: 测试结果字典
        :return: 用例信息字典
        """
        # 从JSON获取基础信息（用于查找Word文档）
        json_case_id = case_result.get("case_id", "UNKNOWN")
        
        # 从Word文档提取用例基本信息
        word_case_info = self._extract_case_info_from_word(json_case_id)
        
        # 优先使用Word文档中的信息
        case_id = word_case_info.get("case_id") or json_case_id
        case_name = word_case_info.get("case_name") or case_result.get("case_name", case_id)
        module = word_case_info.get("module") or case_result.get("module", "XXX")

        # 获取第一个失败步骤的信息
        execution_steps = case_result.get("execution_steps", [])
        failed_step = None
        failed_step_index = -1
        failed_step_screenshots = []  # 存储所有失败步骤的截图
        
        # 遍历所有步骤，收集失败步骤的信息
        for idx, step in enumerate(execution_steps):
            step_result = step.get("step_result", "")
            screenshot = step.get("screenshot_path", "")
            
            if step_result == "不通过":
                # 记录第一个失败步骤用于提取预期结果
                if failed_step is None:
                    failed_step = step
                    failed_step_index = idx
                # 获取失败步骤的截图路径（可能是字符串或列表）
                if screenshot:
                    if isinstance(screenshot, list):
                        failed_step_screenshots.extend(screenshot)
                    else:
                        failed_step_screenshots.append(screenshot)

        # 从Word文档中提取步骤信息（输入及操作、期望结果与评估标准）
        word_steps = self._extract_steps_from_word(case_id)
        
        # 构建重现步骤：从Word文档中提取"输入及操作"
        reproduction_steps = self._build_reproduction_steps_from_word(word_steps)
        
        # 构建预期结果：从Word文档中提取所有步骤的"期望结果与评估标准"
        expected_result = self._build_expected_result_from_word(word_steps)
        
        # 如果从Word文档没有获取到预期结果，回退到从JSON获取（取第一个失败步骤的）
        if not expected_result and failed_step:
            expected_output = failed_step.get("expected_output", [""])
            if isinstance(expected_output, list):
                expected_result = "\n".join(expected_output)
            else:
                expected_result = expected_output

        # 构建问题概述：用例名字 + "执行失败"
        problem_summary = f"{case_name}执行失败"

        return {
            "case_id": case_id,
            "case_name": case_name,
            "module": module,
            "problem_summary": problem_summary,
            "reproduction_steps": reproduction_steps,
            "expected_result": expected_result,
            "actual_result": "",  # 不再返回截图路径文本
            "screenshots": failed_step_screenshots,  # 返回截图路径列表
        }

    def _build_reproduction_steps_from_word(self, word_steps: List[Dict[str, str]]) -> str:
        """
        从Word文档提取的步骤信息构建重现步骤描述
        使用"输入及操作"列的值
        :param word_steps: 从Word文档提取的步骤列表
        :return: 重现步骤文本
        """
        if not word_steps:
            return ""
        
        steps = []
        for step in word_steps:
            seq = step.get("seq", 0)
            input_action = step.get("input_action", "").strip()
            if input_action:
                steps.append(f"{seq}. {input_action}")
        
        return "\n".join(steps)

    def _build_expected_result_from_word(self, word_steps: List[Dict[str, str]]) -> str:
        """
        从Word文档提取的步骤信息构建预期结果描述
        包含所有步骤的"期望结果与评估标准"
        :param word_steps: 从Word文档提取的步骤列表
        :return: 预期结果文本
        """
        if not word_steps:
            return ""
        
        results = []
        for step in word_steps:
            seq = step.get("seq", 0)
            expected = step.get("expected_result", "").strip()
            if expected:
                results.append(f"{seq}. {expected}")
        
        return "\n".join(results)

    def _set_cell_value(self, cell, text: str, color: Optional[RGBColor] = None, auto_height: bool = False):
        """
        设置单元格的值，保留原有格式，只修改文本内容
        启用自动换行以支持长英文字符串，支持自动调整行高
        :param cell: 单元格对象
        :param text: 文本内容
        :param color: 字体颜色
        :param auto_height: 是否自动调整行高（移除固定高度限制）
        """
        # 启用单元格自动换行
        tc = cell._tc
        tcPr = tc.tcPr
        if tcPr is not None:
            # 查找并移除 noWrap 元素（使用 qn 命名空间）
            noWrap_elem = tcPr.find(qn('w:noWrap'))
            if noWrap_elem is not None:
                tcPr.remove(noWrap_elem)
            
            # 如果需要自动调整行高，移除固定高度限制（trHeight）
            if auto_height:
                # 获取单元格所在行
                tr = tc.getparent()
                if tr is not None and tr.tag.endswith('tr'):
                    trPr = tr.find(qn('w:trPr'))
                    if trPr is not None:
                        # 查找并移除 trHeight 元素
                        trHeight = trPr.find(qn('w:trHeight'))
                        if trHeight is not None:
                            trPr.remove(trHeight)
        
        # 获取单元格中的所有段落
        paragraphs = cell.paragraphs
        if not paragraphs:
            # 如果没有段落，创建一个
            cell.text = text
            if color and cell.paragraphs and cell.paragraphs[0].runs:
                run = cell.paragraphs[0].runs[0]
                run.font.color.rgb = color
                # 设置字体为仿宋，字号为五号(10.5pt)
                run.font.name = '仿宋'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')
                run.font.size = Pt(10.5)
            return
        
        # 使用第一个段落，保留其格式
        para = paragraphs[0]
        
        # 设置段落属性：允许西文在单词中间换行
        pPr = para._p.get_or_add_pPr()
        # 添加 <w:cantSplit/> 元素的反面 - 允许在单词中间换行
        # 在 Word XML 中，使用 <w:cantSplit w:val="0"/> 或添加 <w:wordWrap/> 来实现
        from docx.oxml import parse_xml as oxml_parse_xml
        # 添加 wordWrap 元素允许西文在单词中间换行
        wordWrap_elem = oxml_parse_xml(r'<w:wordWrap {} w:val="1"/>'.format(nsdecls('w')))
        pPr.append(wordWrap_elem)
        
        # 如果段落中有runs，修改第一个run的文本
        if para.runs:
            run = para.runs[0]
            run.text = text
            if color:
                run.font.color.rgb = color
            # 设置字体为仿宋，字号为五号(10.5pt)
            run.font.name = '仿宋'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋')
            run.font.size = Pt(10.5)
        else:
            # 如果没有runs，添加一个新的run
            run = para.add_run(text)
            if color:
                run.font.color.rgb = color

    def _remove_template_titles(self, doc: Document):
        """删除模板中原有的标题段落"""
        # 获取body中所有子元素
        body = doc._element.body
        to_remove = []
        
        for element in body:
            # 检查是否是段落
            if element.tag.endswith('p'):
                # 获取段落文本
                text = element.text or ''
                # 收集所有t标签的文本
                for t in element.iter():
                    if t.tag.endswith('t'):
                        text += t.text or ''
                
                # 如果段落包含标题文本，标记为删除
                if "附录C-软件问题报告单" in text or text.strip() == "软件问题报告单":
                    to_remove.append(element)
        
        # 删除标记的段落
        for element in to_remove:
            body.remove(element)

    def _adjust_table_cell_widths(self, table: Table, template_table: Table = None):
        """
        调整表格列宽
        保持与模板文件完全一致，不修改任何单元格宽度
        仅设置表格布局为固定宽度以防止自动调整
        """
        
        # 设置表格布局为固定宽度（防止自动调整）
        tbl = table._tbl
        tblPr = tbl.tblPr
        if tblPr is not None:
            tblLayout = tblPr.tblLayout
            if tblLayout is None:
                tblLayout = parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>')
                tblPr.append(tblLayout)
            else:
                tblLayout.set(qn('w:type'), 'fixed')
        
        # 保持模板原有的单元格宽度，不做任何修改
        # 模板文件中的 tcW 和 gridSpan 已经定义好了合适的宽度

    def _insert_screenshots_to_cell(self, cell, screenshot_paths: List[str], max_width: float = 1.0):
        """
        在单元格中插入截图图片
        参考 WordReportFiller.insert_images_after_placeholder 设置最大宽度
        :param cell: 单元格对象
        :param screenshot_paths: 截图路径列表
        :param max_width: 图片最大宽度（英寸），默认1.0英寸
        """
        if not screenshot_paths:
            return
        
        # 清空单元格现有内容
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.clear()
        
        # 获取第一个段落用于插入图片
        if cell.paragraphs:
            para = cell.paragraphs[0]
        else:
            para = cell.add_paragraph()
        
        # 逐个插入图片
        for img_idx, img_path in enumerate(screenshot_paths, 1):
            try:
                # 处理图片不存在的情况
                if not os.path.exists(img_path):
                    run = para.add_run(f"[图片不存在: {os.path.basename(img_path)}]")
                    run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                    continue
                
                # 添加图片标题
                run = para.add_run(f"截图 {img_idx}: ")
                run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                try:
                    run.font.name = '仿宋'
                except Exception:
                    pass
                try:
                    run.font.size = Pt(10.5)
                except Exception:
                    pass
                
                # 添加图片（限制最大宽度为2英寸）
                run = para.add_run()
                run.add_picture(img_path, width=Inches(max_width))
                
                # 添加换行，因为失败步骤截图数量较多，每个截图后面都插入一个换行符会导致该单元格行高过高，暂时注释该行
                #para.add_run().add_break()
                
            except Exception as e:
                run = para.add_run(f"[插入图片失败: {os.path.basename(img_path)}，错误: {str(e)}]")
                run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                para.add_run().add_break()
        
        # 设置单元格行高为自动调整（随内容变化）
        tc = cell._tc
        tcPr = tc.tcPr
        if tcPr is not None:
            # 移除固定行高限制
            tr = tc.getparent()
            if tr is not None and tr.tag.endswith('tr'):
                trPr = tr.find(qn('w:trPr'))
                if trPr is not None:
                    trHeight = trPr.find(qn('w:trHeight'))
                    if trHeight is not None:
                        trPr.remove(trHeight)

    def _fill_table_data(self, table: Table, data: Dict[str, Any]):
        """根据表格结构填充数据
        
        表格结构说明（9列布局，与模板文件一致）：
        - 基本信息行(Row 0-2): 9列，逻辑上分为左侧标签(2列)+值(3列)+右侧标签(3列)+值(1列)
        - 问题描述行(Row 5-8): 9列，cell0(span=2)+cell1(span=2)+cell2(span=1)+cell3-5(span=6重复)
        """
        # 遍历表格的每一行
        for row_idx, row in enumerate(table.rows):
            cells = row.cells
            if len(cells) < 3:
                continue
            
            # 获取每一行第一个单元格的文本作为key
            first_cell_text = cells[0].text.strip()
            
            # 基本信息行 (Row 0-2): 9列布局
            # cells[0-1]=左侧标签(逻辑2列), cells[2-4]=左侧值(逻辑3列)
            # cells[5-7]=右侧标签(逻辑3列), cells[8]=右侧值(逻辑1列)
            if first_cell_text == "问题标识":
                # 左侧值在 cell 2（但实际因为合并可能需要调整）
                self._set_cell_value(cells[2], data.get("issue_id", ""), color=RGBColor(0xFF, 0x00, 0x00))
                # 右侧值在 cell 8
                if len(cells) > 8:
                    self._set_cell_value(cells[8], data.get("reporter", ""), color=RGBColor(0xFF, 0x00, 0x00))
            
            elif first_cell_text == "测试用例及标识":
                self._set_cell_value(cells[2], data.get("case_display", ""), color=RGBColor(0xFF, 0x00, 0x00))
                if len(cells) > 8:
                    self._set_cell_value(cells[8], data.get("report_date", ""), color=RGBColor(0xFF, 0x00, 0x00))
            
            elif first_cell_text == "软件版本":
                self._set_cell_value(cells[2], data.get("software_version", ""), color=RGBColor(0xFF, 0x00, 0x00))
                if len(cells) > 8:
                    self._set_cell_value(cells[8], data.get("module", ""), color=RGBColor(0xFF, 0x00, 0x00))
            
            # 问题描述部分 (Row 5-8): 遍历查找子标签
            if first_cell_text == "问题描述":
                for col_idx, cell in enumerate(cells):
                    cell_text = cell.text.strip()
                    
                    if cell_text == "问题概述":
                        # value在cell 3（根据模板span=6的单元格）
                        if col_idx + 1 < len(cells):
                            self._set_cell_value(cells[col_idx + 1], data.get("problem_summary", ""), color=RGBColor(0xFF, 0x00, 0x00))
                    
                    elif cell_text == "重现步骤":
                        if col_idx + 1 < len(cells):
                            self._set_cell_value(cells[col_idx + 1], data.get("reproduction_steps", ""), color=RGBColor(0xFF, 0x00, 0x00), auto_height=True)
                    
                    elif cell_text == "执行结果":
                        if col_idx + 1 < len(cells):
                            # 插入截图而不是文本路径
                            screenshots = data.get("screenshots", [])
                            if screenshots:
                                # 使用2英寸最大宽度限制图片尺寸
                                self._insert_screenshots_to_cell(cells[col_idx + 1], screenshots, max_width=1.0)
                            else:
                                self._set_cell_value(cells[col_idx + 1], "无截图", color=RGBColor(0xFF, 0x00, 0x00), auto_height=True)
                    
                    elif cell_text == "预期结果":
                        if col_idx + 1 < len(cells):
                            self._set_cell_value(cells[col_idx + 1], data.get("expected_result", ""), color=RGBColor(0xFF, 0x00, 0x00), auto_height=True)

    def _prepare_fill_data(self, case_result: Dict[str, Any]) -> Dict[str, str]:
        """准备填充数据"""
        case_info = self._extract_case_info(case_result)
        issue_id = self._generate_issue_id(case_info["case_id"])
        reporter = self.config_manager.get_issue_reporter()
        software_version = self.config_manager.get_software_version()
        report_date = datetime.now().strftime("%Y/%m/%d")
        
        return {
            "issue_id": issue_id,
            "reporter": reporter,
            "case_display": f"{case_info['case_name']}({case_info['case_id']})",
            "report_date": report_date,
            "software_version": software_version,
            "module": case_info['module'],
            "problem_summary": case_info['problem_summary'],
            "reproduction_steps": case_info['reproduction_steps'],
            "expected_result": case_info['expected_result'],
            "actual_result": case_info['actual_result'],
            "screenshots": case_info.get('screenshots', []),  # 添加截图路径列表
        }

    def fill_issue_report(self, case_results: List[Dict[str, Any]], output_file: str = None) -> str:
        """
        填充问题报告单
        :param case_results: 测试结果列表
        :param output_file: 输出文件路径（可选）
        :return: 生成的报告文件路径
        """
        if output_file is None:
            output_file = self.config_manager.get_issue_report_output()

        # 筛选失败的用例
        failed_cases = [
            result for result in case_results
            if result.get("overall_result") == "不通过"
        ]

        if not failed_cases:
            print("没有失败的用例，不生成问题报告单")
            return None

        # 加载模板文件
        template_file = self.config_manager.get_issue_report_template()
        template_doc = None
        if os.path.exists(template_file):
            try:
                template_doc = Document(template_file)
                print(f"已加载模板文件: {template_file}")
            except Exception as e:
                print(f"加载模板文件失败: {e}，将使用默认表格结构")

        if template_doc:
            # 使用模板文档，直接填充数据后保存
            doc = template_doc
            
            # 添加标题（检查是否已有，避免重复）
            self._add_titles_to_doc(doc)
            
            # 填充数据到第一个表格
            if doc.tables:
                table = doc.tables[0]
                self._fill_table_data(table, self._prepare_fill_data(failed_cases[0]))
                self._adjust_table_cell_widths(table)
            
            # 处理剩余的用例（每个用例添加一个表格）
            for case_result in failed_cases[1:]:
                doc.add_page_break()
                # 复制模板中的表格（使用deepcopy保留所有属性）
                if doc.tables:
                    from copy import deepcopy
                    source_table = doc.tables[0]
                    new_tbl = deepcopy(source_table._tbl)
                    # 在分页符段落后插入表格，而不是追加到body末尾
                    last_para = doc.paragraphs[-1]
                    last_para._element.addnext(new_tbl)
                    new_table = doc.tables[-1]
                    self._fill_table_data(new_table, self._prepare_fill_data(case_result))
                    self._adjust_table_cell_widths(new_table)
        else:
            # 没有模板时，使用简化逻辑（这里省略了详细实现）
            doc = Document()
            # ...

        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 保存文档
        doc.save(output_file)
        print(f"问题报告单已生成: {output_file}")
        print(f"共记录 {len(failed_cases)} 个失败用例")

        return output_file

    def append_failed_case(self, case_result: Dict[str, Any], output_file: str = None) -> str:
        """
        向问题报告单追加一个失败用例（用于实时回填）
        :param case_result: 单个测试结果字典
        :param output_file: 输出文件路径（可选）
        :return: 生成的报告文件路径
        """
        if case_result.get("overall_result") != "不通过":
            return None

        if output_file is None:
            output_file = self.config_manager.get_issue_report_output()

        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 加载模板文件
        template_file = self.config_manager.get_issue_report_template()
        template_doc = None
        
        # 检查是否是第一次创建文件
        is_first = not os.path.exists(output_file)
        
        if os.path.exists(template_file):
            try:
                template_doc = Document(template_file)
            except Exception as e:
                print(f"加载模板文件失败: {e}")

        if is_first:
            # 第一次创建：直接使用模板文档
            if template_doc:
                doc = template_doc
                # 删除模板中原有的标题（由汇总报告统一添加）
                self._remove_template_titles(doc)
                # 填充数据到第一个表格
                if doc.tables:
                    table = doc.tables[0]
                    self._fill_table_data(table, self._prepare_fill_data(case_result))
                    self._adjust_table_cell_widths(table)
            else:
                doc = Document()
                # 创建基本表格并填充数据
                # ...
        else:
            # 追加模式：打开现有文件
            doc = Document(output_file)
            # 添加分页符
            doc.add_page_break()
            
            if template_doc and template_doc.tables:
                # 追加用例不添加标题，直接复制模板表格
                # 使用deepcopy来保留表格的所有属性（包括列宽）
                from copy import deepcopy
                template_table = template_doc.tables[0]
                new_tbl = deepcopy(template_table._tbl)
                # 在分页符段落后插入表格，而不是追加到body末尾
                last_para = doc.paragraphs[-1]
                last_para._element.addnext(new_tbl)
                new_table = doc.tables[-1]
                # 填充数据
                self._fill_table_data(new_table, self._prepare_fill_data(case_result))
                self._adjust_table_cell_widths(new_table)
            else:
                # 使用默认表格
                pass  # 简化处理

        # 保存文档
        doc.save(output_file)
        print(f"已追加失败用例 {case_result.get('case_id')} 到问题报告单")

        return output_file
