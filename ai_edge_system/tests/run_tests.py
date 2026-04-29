import unittest
import os
import sys
import datetime
import logging
from unittest.mock import MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Pre-mock deepface just in case, though test files do it too
sys.modules['deepface'] = MagicMock()

def setup_logging(timestamp):
    """Configure logging to file and console."""
    log_dir = os.path.join('tests', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f'test_run_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

def generate_report(results, duration, timestamp, total, passed, failed, errors):
    """Generate a Markdown report."""
    report_dir = os.path.join('tests', 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, f'test_report_{timestamp}.md')
    
    md_lines = []
    md_lines.append(f"# 测试报告 (Test Report)")
    md_lines.append(f"")
    md_lines.append(f"**测试日期 (Date):** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append(f"")
    md_lines.append(f"**测试人员 (Tester):** Automated Script")
    md_lines.append(f"")
    md_lines.append(f"## 1. 测试概览 (Overview)")
    md_lines.append(f"")
    md_lines.append(f"本次测试由自动脚本执行。")
    md_lines.append(f"")
    md_lines.append(f"**总计运行**: {total} 个测试用例")
    md_lines.append(f"**通过**: {passed}")
    md_lines.append(f"**失败**: {failed}")
    md_lines.append(f"**错误**: {errors}")
    md_lines.append(f"**耗时**: {duration:.3f}s")
    md_lines.append(f"")
    
    if failed == 0 and errors == 0:
        md_lines.append("✅ 所有测试均已通过。")
    else:
        md_lines.append("❌ 存在未通过的测试用例，请检查详情。")
        
    md_lines.append(f"")
    md_lines.append(f"## 2. 测试结果详情 (Detailed Results)")
    md_lines.append(f"")
    
    # Group results by file
    file_results = {}
    for res in results:
        fname = res['file']
        if fname not in file_results:
            file_results[fname] = []
        file_results[fname].append(res)
        
    sorted_files = sorted(file_results.keys())
    
    for filename in sorted_files:
        md_lines.append(f"### `{filename}`")
        md_lines.append(f"")
        md_lines.append(f"| 测试用例 (Test Case) | 描述 (Description) | 结果 (Result) |")
        md_lines.append(f"| :--- | :--- | :--- |")
        for res in file_results[filename]:
            status_icon = "**PASS**"
            if res['status'] == 'FAIL':
                status_icon = "**FAIL** ❌"
            elif res['status'] == 'ERROR':
                status_icon = "**ERROR** ⚠️"
            
            md_lines.append(f"| `{res['name']}` | {res['desc']} | {status_icon} |")
        md_lines.append(f"")

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
        
    return report_file

def run_tests():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = setup_logging(timestamp)
    
    logging.info(f"Starting test execution. Logs: {log_file}")
    
    loader = unittest.TestLoader()
    start_dir = 'tests'
    try:
        suite = loader.discover(start_dir, pattern='test_*.py')
    except Exception as e:
        logging.error(f"Error discovering tests: {e}")
        return

    # Flatten suite
    tests = []
    def collect_tests(suite_or_test):
        if isinstance(suite_or_test, unittest.TestSuite):
            for t in suite_or_test:
                collect_tests(t)
        else:
            tests.append(suite_or_test)
            
    collect_tests(suite)
    
    if not tests:
        logging.warning("No tests found!")
        return
        
    logging.info(f"Found {len(tests)} tests. Running...")
    
    overall_start = datetime.datetime.now()
    results = []
    passed = 0
    failed = 0
    errors = 0
    
    for test in tests:
        # Get metadata
        module_name = test.__module__
        filename = module_name.split('.')[-1] + ".py" if '.' in module_name else module_name + ".py"
        test_name = test._testMethodName
        desc = test._testMethodDoc or "No description"
        desc = desc.strip().split('\n')[0]
        
        logging.info(f"Running {filename}::{test_name}...")
        
        # Run test
        result = unittest.TestResult()
        start_time = datetime.datetime.now()
        test.run(result)
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        status = "PASS"
        if result.failures:
            status = "FAIL"
            failed += 1
            logging.error(f"FAIL: {filename}::{test_name} - {result.failures[0][1]}")
        elif result.errors:
            status = "ERROR"
            errors += 1
            logging.error(f"ERROR: {filename}::{test_name} - {result.errors[0][1]}")
        else:
            passed += 1
            logging.info(f"PASS: {filename}::{test_name} ({duration:.3f}s)")
            
        results.append({
            'file': filename,
            'name': test_name,
            'desc': desc,
            'status': status
        })

    total_duration = (datetime.datetime.now() - overall_start).total_seconds()
    
    report_file = generate_report(results, total_duration, timestamp, len(tests), passed, failed, errors)
    
    logging.info(f"Test execution completed in {total_duration:.3f}s")
    logging.info(f"Report generated: {report_file}")
    print(f"\nTest run completed. Report: {report_file}")

if __name__ == "__main__":
    run_tests()
