import sys
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

def run_tests():
    # Setup directories
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if we are inside the 'tests' directory
    if os.path.basename(script_dir) == 'tests':
        project_root = os.path.dirname(script_dir)
        tests_dir = script_dir
    else:
        project_root = script_dir
        tests_dir = os.path.join(project_root, "tests")
        
    logs_dir = os.path.join(tests_dir, "logs")
    reports_dir = os.path.join(tests_dir, "reports")
    
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f"test_run_{timestamp}.log")
    report_file = os.path.join(reports_dir, f"test_report_{timestamp}.md")
    xml_report_file = os.path.join(reports_dir, f"temp_result_{timestamp}.xml")
    
    print(f"Starting test run at {timestamp}...")
    print(f"Project root: {project_root}")
    print(f"Logs will be saved to: {log_file}")
    print(f"Report will be saved to: {report_file}")
    
    # Command to run pytest
    # -v: verbose output
    # --junitxml: generate XML report for parsing
    
    # Allow passing specific test paths or arguments from command line
    test_args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]
    
    cmd = [
        sys.executable, "-m", "pytest", 
        *test_args,
        f"--junitxml={xml_report_file}",
        "-v"
    ]
    
    exit_code = 0
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            # Write header to log
            f.write(f"Test Run: {timestamp}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write("-" * 80 + "\n")
            
            # Run pytest, capturing output
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                cwd=project_root,
                env=os.environ.copy()
            )
            
            # Stream output to console and file
            for line in process.stdout:
                sys.stdout.write(line)
                f.write(line)
                
            exit_code = process.wait()
            
        # Generate Markdown Report from XML
        if os.path.exists(xml_report_file):
            generate_markdown_report(xml_report_file, report_file, timestamp, exit_code)
            # Cleanup XML file after report generation
            os.remove(xml_report_file)
        else:
            print("Error: JUnit XML report was not generated.")
            
    except Exception as e:
        print(f"An error occurred during test execution: {e}")
        exit_code = 1
        
    return exit_code

def generate_markdown_report(xml_file, md_file, timestamp, exit_code):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Test Suite Summary
        # pytest junitxml usually puts a root <testsuites> or single <testsuite>
        total_tests = 0
        failures = 0
        errors = 0
        skipped = 0
        time_taken = 0.0
        
        test_cases = []
        
        # Helper to process a testsuite element
        def process_suite(suite):
            nonlocal total_tests, failures, errors, skipped, time_taken
            total_tests += int(suite.get('tests', 0))
            failures += int(suite.get('failures', 0))
            errors += int(suite.get('errors', 0))
            skipped += int(suite.get('skipped', 0))
            time_taken += float(suite.get('time', 0))
            
            for tc in suite.iter('testcase'):
                status = "PASS"
                details = ""
                # Check for failure, error, skipped elements
                fail_node = tc.find('failure')
                error_node = tc.find('error')
                skip_node = tc.find('skipped')
                
                if fail_node is not None:
                    status = "FAIL"
                    details = fail_node.get('message', '') or fail_node.text or "Failure"
                elif error_node is not None:
                    status = "ERROR"
                    details = error_node.get('message', '') or error_node.text or "Error"
                elif skip_node is not None:
                    status = "SKIP"
                    details = skip_node.get('message', '') or skip_node.text or "Skipped"
                
                test_cases.append({
                    "name": tc.get('name'),
                    "classname": tc.get('classname'),
                    "time": float(tc.get('time', 0)),
                    "status": status,
                    "details": details
                })

        if root.tag == 'testsuites':
            for suite in root.iter('testsuite'):
                process_suite(suite)
        else:
            process_suite(root)
        
        passed = total_tests - failures - errors - skipped
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        status_emoji = "✅ PASSED" if exit_code == 0 else "❌ FAILED"
        
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(f"# Test Execution Report\n\n")
            f.write(f"**Run ID**: {timestamp}\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Status**: {status_emoji}\n\n")
            
            f.write("## 1. Overview\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"| :--- | :--- |\n")
            f.write(f"| **Total Tests** | {total_tests} |\n")
            f.write(f"| **Passed** | {passed} |\n")
            f.write(f"| **Failed** | {failures} |\n")
            f.write(f"| **Errors** | {errors} |\n")
            f.write(f"| **Skipped** | {skipped} |\n")
            f.write(f"| **Pass Rate** | {pass_rate:.2f}% |\n")
            f.write(f"| **Total Time** | {time_taken:.2f}s |\n\n")
            
            f.write("## 2. Detailed Results\n\n")
            f.write("| Test Case | Module | Time (s) | Status | Details |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            
            for tc in test_cases:
                status_icon = "✅" if tc['status'] == "PASS" else "❌" if tc['status'] in ["FAIL", "ERROR"] else "⚠️"
                # Format details to be table-friendly (remove newlines, limit length)
                raw_details = str(tc['details']).strip()
                details_preview = (raw_details[:100] + '...') if len(raw_details) > 100 else raw_details
                details_preview = details_preview.replace("\n", " ").replace("|", "\|")
                
                f.write(f"| {tc['name']} | {tc['classname']} | {tc['time']:.3f} | {status_icon} {tc['status']} | {details_preview} |\n")
                
        print(f"\nReport generated successfully: {md_file}")
        
    except Exception as e:
        print(f"\nFailed to generate report: {e}")

if __name__ == "__main__":
    sys.exit(run_tests())
