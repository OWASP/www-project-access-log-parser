# Changelog

## Version X.Y.Z (Date)

### New Features

1. **Output Format Control**
   - Introduced `--output-format` option to provide users with control over the log output format, generating .log-formatted output.

2. **Bug Fix: PHPIDS Rule Matching**
   - Fixed an issue where providing the `-p` option without the corresponding `-r` option resulted in an error due to uninitialized variables. Now, the program checks `boolOutputIDS` before calling functions to handle PHPIDS rule matching.

3. **Custom Filter Option**
   - Added the `-c` option to allow users to specify a custom file for filtering logs, enhancing flexibility in detecting suspicious logs.

4. **Improved Missing Parameter Handling**
   - Instead of displaying a generic missing parameter error, the program now prints the name of the missing required parameter.

5. **Bug Fix: File-related Error Handling**
   - Enhanced error handling for file-related issues when the input or output file is missing. The program now provides clearer messages and includes exception handling.

6. **File Type Specification for Directory Input**
   - Added `--file-type` option to specify the types of files to be processed when the input is a directory. Users can specify multiple file types to filter which files are read by the program.

7. **Improved Processing Efficiency for Directories**
   - Implemented threading for parallel file processing when different input files have different output files. This significantly improves processing time. Note: Threading is not applied when multiple threads write to the same output file to avoid potential overwrites and thread locking overhead.

8. **Enhanced Default Filters**
   - Added important filters (SSRF, XXE, and command injection) to the `default_filter.json` file.

9. **JSON Log Format Support**
   - Added support for reading logs in JSON format by introducing a JSON log parser (`jsonLogParser`) to convert JSON log files to Common Log Format (CLF) before processing.

### Other Enhancements

- Improved overall code efficiency and readability.
- Addressed minor bug fixes and optimizations.

