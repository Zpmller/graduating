import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

// Helper to format date
const formatDate = (date) => {
  const pad = (n) => n.toString().padStart(2, '0');
  const yyyy = date.getFullYear();
  const mm = pad(date.getMonth() + 1);
  const dd = pad(date.getDate());
  const hh = pad(date.getHours());
  const min = pad(date.getMinutes());
  const ss = pad(date.getSeconds());
  return `${yyyy}${mm}${dd}_${hh}${mm}${ss}`;
};

const timestamp = formatDate(new Date());
const logsDir = path.join(__dirname, 'logs');
const reportsDir = path.join(__dirname, 'reports');
const logFile = path.join(logsDir, `test_run_${timestamp}.log`);
const reportFile = path.join(reportsDir, `test_report_${timestamp}.md`);
const tempJsonFile = path.join(__dirname, `temp_results_${timestamp}.json`);

// Ensure directories exist
if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
if (!fs.existsSync(reportsDir)) fs.mkdirSync(reportsDir, { recursive: true });

console.log(`Starting test run...`);
console.log(`Log file: ${logFile}`);
console.log(`Report file: ${reportFile}`);

// Create write stream for log file
const logStream = fs.createWriteStream(logFile, { flags: 'a' });

// Run Vitest
// We use two reporters: 'verbose' for console/log output, and 'json' for generating the report
// Note: We need to be careful about how we capture output.
const vitest = spawn(/^win/.test(process.platform) ? 'npx.cmd' : 'npx', [
  'vitest',
  'run',
  '--reporter=verbose',
  '--reporter=json',
  `--outputFile.json=${tempJsonFile}`
], {
  cwd: projectRoot,
  env: { ...process.env, CI: 'true' }, // Force CI mode to avoid watch mode and colors if needed
  stdio: ['inherit', 'pipe', 'pipe']
});

// Pipe output to console and log file
vitest.stdout.on('data', (data) => {
  process.stdout.write(data);
  logStream.write(data);
});

vitest.stderr.on('data', (data) => {
  process.stderr.write(data);
  logStream.write(data);
});

vitest.on('close', (code) => {
  logStream.end();
  console.log(`\nTest run finished with exit code ${code}`);
  
  generateReport(code);
});

function generateReport(exitCode) {
  if (!fs.existsSync(tempJsonFile)) {
    console.error('Error: JSON result file not found. Cannot generate report.');
    return;
  }

  try {
    const rawData = fs.readFileSync(tempJsonFile, 'utf-8');
    const results = JSON.parse(rawData);
    
    // Calculate stats
    const totalTests = results.numTotalTestSuites; // This is suites, let's count tests
    let totalTestCases = 0;
    let passedTests = 0;
    let failedTests = 0;
    let skippedTests = 0;
    let totalDuration = 0;

    // Traverse results
    const processSuite = (suite) => {
        if (suite.assertionResults) {
            suite.assertionResults.forEach(test => {
                totalTestCases++;
                if (test.status === 'passed') passedTests++;
                else if (test.status === 'failed') failedTests++;
                else if (test.status === 'skipped' || test.status === 'pending') skippedTests++;
                
                // Duration is not always directly on test object in some versions, check
                // Usually it has 'duration' in ms
            });
        }
    };
    
    // Recursive traversal if needed, but vitest json structure is usually flat on testResults
    if (results.testResults) {
        results.testResults.forEach(suite => {
            // totalDuration += suite.endTime - suite.startTime; // Approximate
            if (suite.assertionResults) {
                 suite.assertionResults.forEach(test => {
                    totalTestCases++;
                    if (test.status === 'passed') passedTests++;
                    else if (test.status === 'failed') failedTests++;
                    else if (test.status === 'skipped' || test.status === 'pending') skippedTests++;
                 });
            }
        });
    }
    
    // Use top level stats if available
    totalTestCases = results.numTotalTests || totalTestCases;
    passedTests = results.numPassedTests || passedTests;
    failedTests = results.numFailedTests || failedTests;
    // skipped is not always top level
    
    // If stats are missing, we might need to count them manually from testResults
    // Let's rely on what we can find.
    
    const statusIcon = exitCode === 0 ? '✅ PASSED' : '❌ FAILED';
    const passRate = totalTestCases > 0 ? ((passedTests / totalTestCases) * 100).toFixed(2) + '%' : 'N/A';
    
    const startTime = new Date(results.startTime);
    // Vitest JSON might not have total duration at top level, use startTime
    const duration = (Date.now() - startTime.getTime()) / 1000;

    let markdown = `# Test Execution Report

**Run ID**: ${timestamp}
**Status**: ${statusIcon}
**Date**: ${new Date().toLocaleString()}

## 1. Overview
| Metric | Value |
|--------|-------|
| Total Tests | ${totalTestCases} |
| Passed | ${passedTests} |
| Failed | ${failedTests} |
| Skipped | ${totalTestCases - passedTests - failedTests} |
| Pass Rate | ${passRate} |
| Duration | ${duration.toFixed(2)}s |

## 2. Detailed Results

`;

    if (results.testResults) {
        results.testResults.forEach(suite => {
            const suiteName = path.relative(projectRoot, suite.name);
            markdown += `### 📄 ${suiteName}\n\n`;
            markdown += `| Status | Test Case | Duration | Error |\n`;
            markdown += `| :---: | :--- | :---: | :--- |\n`;
            
            if (suite.assertionResults) {
                suite.assertionResults.forEach(test => {
                    const icon = test.status === 'passed' ? '✅' : (test.status === 'failed' ? '❌' : '⚠️');
                    const duration = test.duration ? `${test.duration}ms` : '-';
                    let errorMsg = '';
                    if (test.status === 'failed' && test.failureMessages) {
                         errorMsg = test.failureMessages.join(' ').replace(/\n/g, '<br>').replace(/\|/g, '\\|');
                    }
                    markdown += `| ${icon} | ${test.title} | ${duration} | ${errorMsg} |\n`;
                });
            }
            markdown += '\n';
        });
    }

    fs.writeFileSync(reportFile, markdown);
    console.log(`Report generated: ${reportFile}`);

    // Cleanup
    fs.unlinkSync(tempJsonFile);

  } catch (err) {
    console.error('Error generating report:', err);
  }
}
