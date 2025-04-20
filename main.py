import os
import argparse
import fnmatch
import time
import sys
import re

def read_gitignore(directory):
    gitignore_path = os.path.join(directory, '.gitignore')
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as file:
            for line in file:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    patterns.append(stripped)
    return patterns

def is_ignored(path, patterns, root, output_file, extensions):
    # Check if the path is the output file itself
    if os.path.abspath(path) == os.path.abspath(output_file):
        return True
        
    # Get the basename of the path
    basename = os.path.basename(path)
    
    # Exclude directories that start with '.'
    if os.path.isdir(path) and basename.startswith('.'):
        return True
        
    # Exclude files and folders with "cache" in their name (case insensitive)
    if 'cache' in basename.lower():
        return True
        
    # Exclude files with more than 4 consecutive digits
    if os.path.isfile(path):
        if re.search(r'\d{5,}', basename):  # 5 or more consecutive digits
            return True
            
    # Check if the path matches any of the patterns
    for pattern in patterns:
        if pattern.startswith('/'):
            pattern = pattern[1:]
        if pattern.endswith('/'):
            pattern = pattern[:-1]
        if fnmatch.fnmatch(path, os.path.join(root, pattern)) or fnmatch.fnmatch(os.path.relpath(path, root), pattern):
            return True
        if os.path.isdir(path) and fnmatch.fnmatch(path, os.path.join(root, pattern + '/*')):
            return True
        if any(fnmatch.fnmatch(part, pattern) for part in os.path.relpath(path, root).split(os.sep)):
            return True
    # Check if the file extension is not in the list of extensions to include
    if os.path.isfile(path):
        _, file_extension = os.path.splitext(path)
        if extensions and file_extension[1:].lower() not in extensions:
            return True
    return False

def get_directory_structure(directory, patterns, root_dir, output_file, extensions, indent=''):
    """Generate a string representation of the directory structure."""
    result = []
    
    try:
        items = sorted(os.listdir(directory))
        dirs = [item for item in items if os.path.isdir(os.path.join(directory, item))]
        files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
        
        # Count included and excluded items for statistics
        included_dirs = 0
        excluded_dirs = 0
        included_files = 0
        excluded_files = 0
        
        for d in dirs:
            path = os.path.join(directory, d)
            if not is_ignored(path, patterns, root_dir, output_file, extensions):
                included_dirs += 1
                
                # Add file count indicator
                file_count = count_files(path, patterns, root_dir, output_file, extensions)
                dir_text = f"{indent}📁 {d}/ ({file_count} files)"
                
                result.append(dir_text)
                result.extend(get_directory_structure(path, patterns, root_dir, output_file, extensions, indent + '│  '))
            else:
                excluded_dirs += 1
        
        for f in files:
            path = os.path.join(directory, f)
            if not is_ignored(path, patterns, root_dir, output_file, extensions):
                included_files += 1
                
                # Add file size indicator
                size = os.path.getsize(path)
                size_str = format_file_size(size)
                file_text = f"{indent}📄 {f} ({size_str})"
                
                # Add a visual indicator for file type
                _, ext = os.path.splitext(f)
                if ext:
                    ext = ext[1:].lower()  # Remove the dot and convert to lowercase
                    icon = get_file_icon(ext)
                    file_text = f"{indent}{icon} {f} ({size_str})"
                
                result.append(file_text)
            else:
                excluded_files += 1
        
        # If this is the root directory, add statistics
        if directory == root_dir:
            total_included = count_files(directory, patterns, root_dir, output_file, extensions)
            total_excluded = count_excluded_files(directory, patterns, root_dir, output_file, extensions)
            
            result.append("")
            result.append("📊 STATISTICS:")
            result.append(f"   Total files included: {total_included}")
            result.append(f"   Total files excluded: {total_excluded}")
            result.append(f"   Total files: {total_included + total_excluded}")
            
    except PermissionError:
        result.append(f"{indent}🔒 Permission denied")
    except Exception as e:
        result.append(f"{indent}❌ Error: {str(e)}")
    
    return result

def count_files(directory, patterns, root_dir, output_file, extensions):
    """Count the number of files that would be included in the output."""
    count = 0
    for root, dirs, files in os.walk(directory):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), patterns, root_dir, output_file, extensions)]
        
        # Count non-ignored files
        for file in files:
            file_path = os.path.join(root, file)
            if not is_ignored(file_path, patterns, root_dir, output_file, extensions):
                count += 1
    return count

def count_excluded_files(directory, patterns, root_dir, output_file, extensions):
    """Count the number of files that would be excluded from the output."""
    count = 0
    for root, dirs, files in os.walk(directory):
        # Count ignored directories
        excluded_dirs = []
        for d in dirs:
            if is_ignored(os.path.join(root, d), patterns, root_dir, output_file, extensions):
                excluded_dirs.append(d)
                
        # Remove excluded directories from dirs to avoid walking them
        for d in excluded_dirs:
            dirs.remove(d)
        
        # Count ignored files
        for file in files:
            file_path = os.path.join(root, file)
            if is_ignored(file_path, patterns, root_dir, output_file, extensions):
                count += 1
    return count

def format_file_size(size_in_bytes):
    """Convert file size in bytes to a human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"

def get_file_icon(extension):
    """Return an appropriate icon for the file type."""
    icons = {
        # Code
        'py': '🐍',
        'js': '📜',
        'ts': '📜',
        'jsx': '⚛️',
        'tsx': '⚛️',
        'html': '🌐',
        'css': '🎨',
        'scss': '🎨',
        'sass': '🎨',
        'java': '☕',
        'c': '📟',
        'cpp': '📟',
        'h': '📟',
        'cs': '📟',
        'php': '🐘',
        'rb': '💎',
        'go': '🔹',
        'rs': '🦀',
        'swift': '🔶',
        'kt': '🔷',
        
        # Data
        'json': '📊',
        'xml': '📊',
        'csv': '📊',
        'yaml': '📊',
        'yml': '📊',
        'toml': '📊',
        'sql': '🗃️',
        
        # Documents
        'md': '📝',
        'txt': '📄',
        'pdf': '📑',
        'doc': '📘',
        'docx': '📘',
        'xls': '📗',
        'xlsx': '📗',
        'ppt': '📙',
        'pptx': '📙',
        
        # Images
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'png': '🖼️',
        'gif': '🖼️',
        'svg': '🖼️',
        'ico': '🖼️',
        'webp': '🖼️',
        
        # Archives
        'zip': '📦',
        'rar': '📦',
        'tar': '📦',
        'gz': '📦',
        '7z': '📦',
        
        # Config
        'ini': '⚙️',
        'conf': '⚙️',
        'config': '⚙️',
        'env': '⚙️',
        
        # Executable
        'exe': '⚡',
        'sh': '⚡',
        'bat': '⚡',
        'cmd': '⚡',
    }
    
    return icons.get(extension, '📄')  # Default icon if extension not found

def process_directory(directory, output_file, extensions):
    patterns = read_gitignore(directory)
    patterns.append('.git/')  # Skip .git folder files

    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write directory structure at the beginning
        outfile.write("=" * 60 + "\n")
        outfile.write("=== PROJECT DIRECTORY STRUCTURE ===\n")
        outfile.write("=" * 60 + "\n\n")
        
        # Get the project name from the directory
        project_name = os.path.basename(os.path.normpath(directory))
        outfile.write(f"📂 PROJECT: {project_name}\n")
        outfile.write(f"📅 DATE: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        structure = get_directory_structure(directory, patterns, directory, output_file, extensions)
        outfile.write('\n'.join(structure))
        outfile.write("\n\n")
        outfile.write("=" * 60 + "\n\n")
        
        # Write file exclusion rules applied
        outfile.write("=== EXCLUSION RULES APPLIED ===\n")
        outfile.write("✓ Files and directories from .gitignore\n")
        outfile.write("✓ Directories starting with '.'\n")
        outfile.write("✓ Files with 5+ consecutive digits in filename\n")
        outfile.write("✓ Files and directories with 'cache' in name\n")
        if extensions:
            outfile.write(f"✓ Only including extensions: {', '.join(extensions)}\n")
        outfile.write("\n")
        outfile.write("=" * 60 + "\n\n")

        for root, dirs, files in os.walk(directory):
            # Remove ignored directories from dirs
            dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), patterns, directory, output_file, extensions)]

            for file in files:
                file_path = os.path.join(root, file)
                if is_ignored(file_path, patterns, directory, output_file, extensions):
                    continue

                # Get the relative path to the input directory
                relative_path = os.path.relpath(file_path, directory)
                
                # Get file metadata
                file_size = format_file_size(os.path.getsize(file_path))
                file_mod_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(file_path)))

                # Write header with file information
                outfile.write(f"=== {relative_path} ===\n")
                outfile.write(f"Size: {file_size} | Last Modified: {file_mod_time}\n")
                outfile.write("-" * 60 + "\n")

                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        outfile.write(content)
                        outfile.write("\n\n")  # Add a separator between files
                except UnicodeDecodeError:
                    print(f"Skipping file: {relative_path} (Unicode decode error)")
                    outfile.write("[Binary file - contents not displayed]\n\n")
                except Exception as e:
                    print(f"Error processing file: {relative_path} ({str(e)})")
                    outfile.write(f"[Error reading file: {str(e)}]\n\n")

            # Update the animated text
            sys.stdout.write(f"\rMerging into {os.path.basename(output_file)}{'.' * (int(time.time()) % 4)}")
            sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description='Combine code files into a continuous text file.')
    parser.add_argument('directory', help='Directory to process')
    parser.add_argument('-o', '--output', help='Optional: Output file path', nargs='?', default=None)
    parser.add_argument('-e', '--extensions', help='Comma-separated list of file extensions to include', default='')
    args = parser.parse_args()

    extensions = [ext.lower() for ext in args.extensions.split(',')] if args.extensions else []

    # Resolve the actual path of the directory
    directory_path = os.path.realpath(args.directory)

    # If no output is provided, create one based on the directory name
    if args.output:
        output_file = os.path.realpath(args.output)
    else:
        # Get the name of the last directory in the path
        directory_name = os.path.basename(os.path.normpath(directory_path))
        # Construct the output file path using the directory name and appending '.txt'
        output_file = os.path.join(directory_path, '..', f"{directory_name}.txt")

    # Ensure the output file path is absolute
    output_file = os.path.abspath(output_file)

    process_directory(directory_path, output_file, extensions)
    print(f"\nFiles combined into: {output_file}")

if __name__ == '__main__':
    main()